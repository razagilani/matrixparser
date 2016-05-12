"""This module should contain subclasses of QuoteParser for specific
suppliers, each one in a separate file.
"""
from brokerage.quote_parsers.source import SourceMatrixParser
from .aep import AEPMatrixParser
from .amerigreen import AmerigreenMatrixParser
from brokerage.quote_parsers.guttman_electric import GuttmanElectric
from brokerage.quote_parsers.guttman_gas import GuttmanGas
from .champion import ChampionMatrixParser
from .constellation import ConstellationMatrixParser
from .direct_energy import DirectEnergyMatrixParser
from .liberty import LibertyMatrixParser
from .entrust import EntrustMatrixParser
from .major_energy import MajorEnergyMatrixParser
from .usge_gas import USGEGasMatrixParser
from .usge_electric import USGEElectricMatrixParser
from .sfe import SFEMatrixParser
from .gee_electric import GEEMatrixParser
from .volunteer import VolunteerMatrixParser
from .gee_gas_nj import GEEGasNJParser
from .gee_gas_ny import GEEGasNYParser
from .spark import SparkMatrixParser
from .suez_electric import SuezElectricParser

# mapping of each matrix format's primary key in the database to its
# QuoteParser subclass. each time a subclass is written for a new format,
# add it to this dictionary.
CLASSES_FOR_FORMATS = {
    6: AEPMatrixParser,
    11: AmerigreenMatrixParser,
    7: ChampionMatrixParser,
    3: ConstellationMatrixParser,
    8: DirectEnergyMatrixParser,
    1: LibertyMatrixParser,
    2: EntrustMatrixParser,
    10: MajorEnergyMatrixParser,
    9: SFEMatrixParser,
    4: USGEGasMatrixParser,
    14: USGEElectricMatrixParser,
    13: GEEMatrixParser,
    12: VolunteerMatrixParser,
    17: GuttmanGas,
    18: GuttmanElectric,
    19: SparkMatrixParser,
    20: GEEGasNYParser,
    21: GEEGasNJParser,
    22: SourceMatrixParser,
    23: SuezElectricParser,
}

