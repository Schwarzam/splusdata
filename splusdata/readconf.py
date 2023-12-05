import argparse
import splusdata
import pandas as pd
import os
import inspect

from astropy.table import Table

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
    
operations = [
    'stamp',
    'lupton_rgb',
    'trilogy_image'
    'field_frame',
    'checkcoords',
    'query'
]

def filter_info(info, function):
    # Get the signature of the function
    func_signature = inspect.signature(function)

    # Extract parameter names from the function
    expected_keys = [param.name for param in func_signature.parameters.values()]

    # Filter the dictionary
    filtered_dict = {k: info[k] for k in expected_keys if k in info}
    
    return filtered_dict

def create_stamp_name(info, output_folder):
    filename = os.path.join(output_folder, f"{info['ra']}_{info['dec']}_{info['size']}_{info['band']}.fits")
    return filename

def create_image_name(info, output_folder):
    filename = os.path.join(output_folder, f"{info['ra']}_{info['dec']}_{info['size']}.png")
    return filename

def create_field_name(info, output_folder):
    filename = os.path.join(output_folder, f"{info['field']}_{info['band']}.fits")
    return filename
    
def handle_operation(operation : str, info, conn):
    output_folder = info['output_folder']
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    if operation == 'stamp':
        filename = create_stamp_name(info, output_folder)
        info = filter_info(info, conn.stamp)
        conn.stamp( filename=filename, **info )
    
    elif operation == 'lupton_rgb':
        filename = create_image_name(info, output_folder)
        info = filter_info(info, conn.lupton_rgb)
        conn.lupton_rgb( filename=filename, **info )
    
    elif operation == 'trilogy_image':
        filename = create_image_name(info, output_folder)
        info = filter_info(info, conn.trilogy_image)
        conn.trilogy_image( filename=filename, **info )

    elif operation == 'field_frame':
        filename = create_field_name(info, output_folder)
        info = filter_info(info, conn.field_frame)
        conn.field_frame( filename=filename, **info )

    elif operation == 'checkcoords':
        info = filter_info(info, conn.checkcoords)
        try:
            data = conn.checkcoords( **info )
            data["ra"] = info["ra"]
            data["dec"] = info["dec"]
        except:
            data = {"ra": info["ra"], "dec": info["dec"], "field": None, "distance": None, "public": None, "internal": None}
        return data
    elif operation == 'query':
        if "query" not in info:
            raise ValueError("Query not specified")
        
        filename = os.path.join(output_folder, "query.fits")

        if "upload_table" in info:
            if not os.path.exists(info["upload_table"]):
                raise ValueError("File {} does not exist".format(info["upload_table"]))
            
            try:
                file = pd.read_csv(info["upload_table"])
                info = filter_info(info, conn.query)
                data = conn.query(table_upload=file,  **info )
                data.write(filename, overwrite=True)
            except Exception as e:
                print(e)

        else:
            
            info = filter_info(info, conn.query)
            try:
                data = conn.query( **info )
                data.write(filename, overwrite=True)
            except Exception as e:
                print(e)

            

def get_coordinates_col(df : pd.DataFrame):
    ra = None
    dec = None
    
    for col in df.columns:
        if col.lower() == "ra":
            ra = col
        elif col.lower() == "dec":
            dec = col
    
    if ra is None or dec is None:
        raise ValueError("File does not have columns 'ra' and 'dec'")
    
    return ra, dec
            

def handle_operation_type(operation_data, conn):
    checkcoords_list = []
    if isinstance(operation_data["type"], str):
        operations = [operation_data["type"]]
    elif isinstance(operation_data["type"], list):
        operations = operation_data["type"]
    else:
        raise ValueError("Operation type must be a string or a list of strings")
    
    for op in operations:
        if op not in operations:
            raise ValueError("Operation type not supported: {}".format(op))
        
    if "file_path" in operation_data:
        try:
            df = pd.read_csv(operation_data["file_path"])
        except:
            df = Table.read(operation_data["file_path"]).to_pandas()

        ra_col, dec_col = get_coordinates_col(df)

        for key, value in df.iterrows():
            info = operation_data
            ## Add ra and dec to info
            info["ra"] = value[ra_col]
            info["dec"] = value[dec_col]
            for op in operations:
                if op == "checkcoords":
                    checkcoords_list.append(handle_operation(op, info, conn))
                else:
                    handle_operation(op, info, conn)
    
    else:
        for op in operations:
            if op == "checkcoords":
                checkcoords_list.append(handle_operation(op, operation_data, conn))
            else:
                handle_operation(op, operation_data, conn)

    if len(checkcoords_list) > 0:
        checkcoords_df = pd.DataFrame(checkcoords_list)
        checkcoords_df.to_csv(os.path.join(operation_data["output_folder"], "checkcoords.csv"), index=False)



def main():
    parser = argparse.ArgumentParser(description='splusdata - Download SPLUS catalogs, FITS and more')
    parser.add_argument('config_file', metavar='config_file', type=str, help='Configuration file')
    
    args = parser.parse_args()
    
    configfile = os.path.join(os.getcwd(), args.config_file)
    stream = open(configfile, 'rb')
    data = load(stream, Loader=Loader)

    try:
        conn = splusdata.Core(data["user"], data["password"])
    except:
        conn = splusdata.Core()
        
    handle_operation_type(data["operation"], conn)

    return 0

        

if '__name__' == '__main__':
    main()  