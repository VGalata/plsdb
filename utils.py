#!/usr/bin/python

import re
import logging
import pandas

##################################################
# MISC
##################################################
def setup_logger(log_level=logging.DEBUG):
    """Logger"""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%y:%m:%d %H:%M:%S'
    )

def split_list(values, size):
    values = list(values)
    for i in range(0, len(values), size):
        yield values[i:(i + size)]

def run_cmd(cmd):
    """
    Run given CMD
    :param cmd: CMD (str)
    :return: cmd (str), status (int), stdout + stderr (str)
    """
    import subprocess
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    p_stdout = p.stdout.read().decode()
    p_comm   = p.communicate()[0]
    p_status = p.returncode
    return cmd, p_status, p_stdout

def mkdir(dpath, p=True):
    import os
    if p and not os.path.exists(dpath):
        os.makedirs(dpath)
    else:
        os.makedirs(dpath)

def proc_mlst_scheme_name(scheme_name):
    import re
    return re.sub('/', '_', re.sub('\s+', '__', scheme_name))

def reproc_mlst_scheme_name(scheme_name):
    import re
    return re.sub('_', '/', re.sub('__', ' ', scheme_name))

##################################################
# Edirect/eutils
##################################################
def run_epost_split(df_file, ofile, header, cmd, df_col, split_size, split_str, **kwargs):
    import pandas, tqdm

    logging.info('CMD: {}'.format(cmd))

    ids = pandas.read_csv(df_file, sep='\t', header=0, dtype=str)[df_col]
    logging.info('There are {} IDs'.format(len(ids)))
    ids.fillna(value='', inplace=True)
    ids = ids.loc[ids != ""]
    ids = set(ids.values)
    if split_str is not None and split_str != "":
        ids_ = set()
        for id_ in ids:
            ids_ = ids_.union(id_.split(split_str))
        ids = ids_
    logging.info('There are {} unique IDs'.format(len(ids)))

    with open(ofile, 'w') as ohandle:
        ohandle.write(header + '\n')
        for chunk in tqdm.tqdm(split_list(ids, split_size)):
            cmd_c = cmd.format(**kwargs, ids=','.join(chunk))
            cmd_c, cmd_s, cmd_o = run_cmd(cmd_c)
            assert cmd_s == 0, 'CMD: {}: {}\n{}'.format(cmd_c, cmd_s, cmd_o)
            # checks
            if re.search('elink', cmd):
                for line in cmd_o.split('\n'):
                    if line == '':
                        continue
                    if re.search('\t', line):
                        i_n, i_s = line.split('\t')
                    else:
                        i_n = line.strip()
                        i_s = None
                    assert i_n in ids, 'Unexpected nuccore ID {}'.format(i_n)
                    # assert i_s is None or (not re.search(';', i_s)), 'Multiple hits for {}: {}'.format(i_n, i_s)
            else:
                found = [l.split('\t')[0] for l in cmd_o.split('\n') if l != '']
                not_found = list(set(chunk).difference(found)) # not found IDs
                une_found = list(set(found).difference(chunk)) # unexpected IDs, i.e. should not be searched
                # assert len(not_found) == 0, 'Not found: {}: {}, ...'.format(len(not_found), ', '.join([str(s) for s in not_found[0:5]]))
                assert len(une_found) == 0, 'Not expected: {}: {}, ...'.format(len(une_found), ', '.join([str(s) for s in une_found[0:5]]))
                if len(not_found) > 0:
                    logging.warn('Could not find: %s' % ', '.join([str(s) for s in not_found]))
            # save
            ohandle.write(cmd_o)

##################################################
# LOCATIONS
##################################################
# Parsing location information from NCBI (BioSample) using GoogleMaps

# Exceptions: need to change string to get result from GMaps
location_exceptions = {
    'Jigalong, Australia': 'Australia, Jigalong', # ordering matters
    'China: Jilin Pesticide Plant': 'China: Jilin', # non-loc. info.
    'Korea: Gwangyang Province': 'Korea: Gwangyang', #
    'China:Pearl Spring': 'China', # unknown location
    'China: the China South Sea': 'South China Sea', # otherwise maps to US
    'China: Changji city, Xinjiang Uygur Autonomous Region': 'China: Changji', # maps to loc. in China near border to S: Korea
    'China: Southern China': 'China', # otherwise maps to US
}

# Strings used for missing locations (to avoid unneccessary queries)
location_missing = [
    "",
    "-",
    "na", "n/a", "n.a.",
    "missing", "none",
    "not applicable", "not available", "not collected", "not determined", "not recorded",
    "unavailable", "unknown", "unspecified",
]

def loc_is_missing(loc_str):
    for na_str in location_missing:
        if re.fullmatch(na_str, loc_str, re.IGNORECASE):
            return True
    return False

def preproc_loc_str(loc_str):
    """
    Pre-process location string
    Return processed result or None (for "no location")
    """
    import pandas
    if pandas.isnull(loc_str):
        return None
    # removes unicode or other "unexpected" chars
    loc_str = loc_str.encode('ascii','ignore').decode()
    # trailing/leading whitespaces
    loc_str = loc_str.strip()
    # strings known to encode "empty" entries
    if loc_is_missing(loc_str):
        return None
    # exceptions
    if loc_str in location_exceptions:
        loc_str = location_exceptions[loc_str]
    return loc_str

def add_dotzero(loc_str):
    """
    Add ".0" to a coordinate of it is only an int
    E.g. "23N" -> "23.0N"
    Required for correct query processing
    """
    if re.match(r'[0-9]+[N|S|W|E]', loc_str):
        loc_str = re.sub(r'([0-9]+)',r'\1.0',loc_str)
    return loc_str

def preproc_loc_coords(loc_str):
    """
    Pre-process location coordinate string
    Returns tuple of coordinates or None (for "no location")
    """
    import pandas
    if loc_str is None or pandas.isnull(loc_str):
        return None
    if re.fullmatch(r'[0-9]+(\.[0-9]+)?\s*[N|S][\s,]*[0-9]+(\.[0-9]+)?\s*[W|E]', loc_str):
        matches = [add_dotzero(re.sub(' ','',m.group())) for m in re.finditer(r'[0-9]+(\.[0-9]+)?\s*[N|S|W|E]', loc_str)]
        assert len(matches) == 2, 'Problem to parse %s' % loc_str
        return matches[0], matches[1]
    elif re.fullmatch(r'[0-9]+(\.[0-9]+)?[\s,]*[0-9]+(\.[0-9]+)?', loc_str):
        matches = [re.sub(' ','',m.group()) for m in re.finditer(r'[0-9]+(\.[0-9]+)?', loc_str)]
        assert len(matches) == 2, 'Problem to parse %s' % loc_str
        return matches[0], matches[1]
    else:
        return None

def parse_location(loc_str, api_key, is_name=True):
    """
    Input: Location name or coordinates as string
    Returns {'lat': <float>, 'lng': <float>} if successful otherwise None
    Uses https://github.com/googlemaps/google-maps-services-python
    """
    import time
    import googlemaps

    if pandas.isnull(loc_str):
        return None

    input = loc_str
    gmaps = googlemaps.Client(key=api_key)
    loc = None
    # query
    loc = None
    if is_name or re.search(r'N|W|E|S', loc_str[0]) or re.search(r'N|W|E|S', loc_str[1]):
        loc = gmaps.geocode(loc_str)
        time.sleep(1)
    else:
        loc = gmaps.reverse_geocode(loc_str)
        time.sleep(1)
    # no hit
    if len(loc) == 0:
        logging.info('Location: no hit: %s' % input)
        return None
    # got location
    assert 'geometry' in loc[0], 'Location: hit w/o geometry: %s' % input
    assert 'location' in loc[0]['geometry'], 'Location: hit w/o coordinates: %s' % input
    return loc[0]['geometry']['location']
