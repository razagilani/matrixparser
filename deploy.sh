#/bin/bash


# Give only one command-line arg.
if [ -z $1 ]; then
    echo "Usage: $0 [dev|prod]"
    exit 1
fi


trap ctrl_c INT
function ctrl_c() {
    echo ""
    echo "Exiting deployment!"
    exit 1
}


# Infer the developer's bitbucket username.
hg_repo=`grep "default =" .hg/hgrc | cut -d'@' -f2`
hg_username=`grep "username = " ~/.hgrc | cut -d'<' -f2 | cut -d'@' -f1`
read -p "Enter password for Bitbucket user ${hg_username}: " -s hg_password
echo ""


# Revision information.
basepath=`pwd`
current_branch=`hg branch`
hg_rev=`hg id -i`
hg_rev=`echo ${hg_rev} | tr -d '+'`

if [[ "${hg_rev}" =~ "+" ]]; then
    echo "Uncommitted changes!"
    exit 3
fi

# before starting the deployment process, check that Bitbucket credentials are
# right and the revision exists.
# wget prints the URL (including password) to stdout if it succeeds, so only
# print the output if it failed
output=$(wget --method=HEAD "https://$hg_username:$hg_password@$hg_repo/get/$hg_rev.zip" --no-verbose 2>&1)
if [[ $? != 0 ]]; then
    echo $output
    exit
fi


# Do extra validation if pushing to prod.
if [ "$1" == "prod" ]; then
    read -n 1 -p "Deploy from ${hg_repo} branch ${current_branch} (y/n)?" repo_confirm
    echo ""
    
    if [ "${repo_confirm}" = "n" ]; then
        exit 0
    fi
    
    read -n 1 -p "Clobber prod (y/n)? " clobber_confirm
    echo ""
    
    if [ "${clobber_confirm}" = "y" ]; then
        secs=(5 4 3 2 1)
        for i in ${secs[@]}; do
            echo -ne "Deploying branch ${current_branch} (rev ${hg_rev}) to PROD in ${i} ...   \r"
            sleep 1
        done
    
        echo "Deploying!!"
        echo ""
    else
        echo "Cancelling deployment."
        exit 1
    fi
fi


echo "Deploying revision ${hg_rev} on ${current_branch} ..."

cd deployment
ansible-playbook -i $1 app.yml --extra-vars "revision=${hg_rev} hg_username=${hg_username} hg_password=${hg_password} hg_branch=${current_branch} hg_repo=${hg_repo}"
