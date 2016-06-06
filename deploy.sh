#/bin/bash


# PURPOSE: This script is a wrapper around Ansible, our deployment and 
#          provisioning tool. It infers your git username, repository,
#          and Bitbucket username. When deploying code, implicitly
#          it deploys from the current revision in your local repo.
#          You must make sure it also exists in your fork.


# Take only one command-line arg: dev or prod.
if [ -z $1 ]; then
    echo "Usage: $0 [dev|prod]"
    exit 1
fi


# Infer the git executable version, only works with > 2.
git_version_str=$(git --version | cut -d ' ' -f3)
if [ ${git_version_str:0:1} -ne 2 ];
then
    echo "Invalid git version: $(git --version). Must be 2 or higher."
    exit 1
fi


# Trap Ctrl+C to stop this script.
trap ctrl_c INT
function ctrl_c() {
    echo ""
    echo "Exiting deployment!"
    exit 1
}


# Capture the user's username
git_repo=`git remote get-url origin | cut -d'@' -f2 | sed 's/:/\//' | sed 's/.git//'`
read -p "Enter bitbucket username: " bitbucket_username
echo ""

if [ -z ${bitbucket_username} ]; then
  echo "username can not be empty"
  exit 1
fi

# Capture the user's password but does not echo to the terminal.
read -p "Enter password for Bitbucket user ${bitbucket_username}: " -s password
echo ""


# Revision information.
basepath=`pwd`
current_branch=`git rev-parse --abbrev-ref HEAD`
git_rev=`git rev-parse HEAD`


# Determine if there are uncommitted changes, if so, abort!
git diff --quiet
if [[ $? -ne 0 ]]; then
    echo "Uncommitted changes!"
    exit 3
fi


# before starting the deployment process, check that Bitbucket credentials are
# right and the revision exists.
# wget prints the URL (including password) to stdout if it succeeds, so only
# print the output if it failed
output=$(wget --method=HEAD "https://${bitbucket_username}:${password}@${git_repo}/get/$git_rev.zip" --no-verbose 2>&1)
if [[ $? != 0 ]]; then
    echo $output
    exit 1
fi


# Do extra validation if pushing to prod.
if [ "$1" == "prod" ]; then
    read -n 1 -p "Deploy from ${git_repo} branch ${current_branch} (y/n)? " repo_confirm
    echo ""
    
    if [ "${repo_confirm}" = "n" ]; then
        exit 0
    fi
    
    read -n 1 -p "Clobber prod (y/n)? " clobber_confirm
    echo ""
    
    if [ "${clobber_confirm}" = "y" ]; then
        secs=(5 4 3 2 1)
        for i in ${secs[@]}; do
            echo -ne "Deploying branch ${current_branch} (rev ${git_rev}) to PROD in ${i} ...   \r"
            sleep 1
        done
    
        echo "Deploying!!"
        echo ""
    else
        echo "Cancelling deployment."
        exit 1
    fi
fi


echo "Deploying revision ${git_rev} on ${current_branch}!"

cd deployment
ansible-playbook -i $1 app.yml --extra-vars "revision=${git_rev} hg_username=${bitbucket_username} hg_password=${password} hg_branch=${current_branch} hg_repo=${git_repo}"
