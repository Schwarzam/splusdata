import setuptools

setuptools.setup(
     name='splusdata',
     version='4.00',
     packages = setuptools.find_packages(),
     author="Gustavo Schwarz",
     author_email="gustavo.b.schwarz@gmail.com",
     description="Download SPLUS catalogs, FITS and more",
     url="https://github.com/schwarzam/splusdata",
     install_requires = ['requests', 'astropy', 'astroquery', 'numpy', 'pandas', 'scipy', 'numpy', 'pillow', 'pyyaml'],
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: Apache Software License"
     ],
     
     entry_points={
        'console_scripts': [
            'splusdata=splusdata.readconf:main',
        ],
    },
 )
#python3 setup.py bdist_wheel
#python3 -m twine upload dist/*
