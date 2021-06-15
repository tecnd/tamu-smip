from datetime import datetime
'''
Temporary fix for missing microsecond field in GraphQL response
'''
def strptime_fix(ts:str) -> datetime:
    fmt = ''
    if len(ts) > 26:
        fmt = '%Y-%m-%dT%H:%M:%S.%f%z'
    elif len(ts) == 25:
        fmt = '%Y-%m-%dT%H:%M:%S%z'
    else:
        raise ValueError('Unrecognized timestamp: ' + ts)
    return datetime.strptime(ts, fmt)
    