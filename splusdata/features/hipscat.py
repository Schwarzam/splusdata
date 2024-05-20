import os
import requests
import re

def _match_patterns(patterns, strings):
    matches = {}
    for string in strings:
        matched_patterns = []
        for pattern in patterns:
            if re.search(pattern, string):
                matched_patterns.append(pattern)
        if matched_patterns:
            matches[string] = matched_patterns
    return matches

def _get_hips_n_margin_links(pattern, dirs_schema, starting_path = "/"):
    patterns = pattern.split("/")
    if patterns[-1] == "":
        patterns = patterns[:-1]
    res = []
    
    for key in dirs_schema.keys():
        if key == "hipscats":
            match_res = _match_patterns(patterns, dirs_schema[key])
            match_res = list(match_res.keys())
            
            if len(match_res) == 0:
                continue
            
            for match in match_res:
                local_res = [os.path.join(starting_path, match), None]
            
                if "margins" in dirs_schema:
                    for margin in dirs_schema["margins"]:
                        if margin.startswith(match):
                            margin = os.path.join(starting_path, margin)
                            local_res[1] = margin
                            break
                
                res.append(local_res)
            
        elif key != "margins":
            res += _get_hips_n_margin_links(pattern, dirs_schema[key], starting_path = os.path.join(starting_path, key))
    return res

def get_hipscats(pattern=None, SERVER_IP = f"https://splus.cloud", HIPS_IP = f"https://splus.cloud/HIPS/catalogs"):
    link = "/api/get_hipscat_available"
    
    res = requests.get(SERVER_IP + link)
    if res.status_code != 200:
        raise ValueError(f"Error: {res.status_code}")
    
    data = res.json()
    if pattern is not None:
        res = _get_hips_n_margin_links(pattern, data)
        data = res
    
        for i in range(len(data)):
            data[i] = [HIPS_IP + data[i][0], HIPS_IP + data[i][1]]
        
    return data