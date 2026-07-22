from enum import StrEnum


class Investor(StrEnum):
    FANNIE_MAE = "fannie_mae"
    FREDDIE_MAC = "freddie_mac"
    BOTH = "both"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RuleType(StrEnum):
    SCHEMA = "schema"
    DATATYPE = "datatype"
    ENUMERATION = "enumeration"
    XLINK = "xlink"
    APPENDIX_H = "appendix_h"
    POLICY = "policy"
    ADVISORY = "advisory"
