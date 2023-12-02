import argparse
import splusdata

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
    


def main():
    parser = argparse.ArgumentParser(description='splusdata - Download SPLUS catalogs, FITS and more')
    parser.add_argument('config_file', metavar='config_file', type=str, help='Configuration file')
    
    
    
    args = parser.parse_args()
    
    # data = load(args.config_file, Loader=Loader)

if '__name__' == '__main__':
    main()