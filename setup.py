import os
from setuptools import setup, find_packages

version = '0.1.1'

proj_dir = os.path.abspath(os.path.dirname(__file__))
reqs = [line.strip()
        for line in open(
                os.path.join(proj_dir, 'requirements.txt'), encoding='utf-8')]
install_requires = [req.split('#egg=')[-1].replace('-', '==')
                    if '#egg=' in req else req
                    for req in reqs]
dependency_links = [req for req in reqs if 'git+' in req]
print(install_requires)
print(dependency_links)

setup(
    name='calval',
    version=version,
    author='Slava Kerner, Amit Aronovitch',
    url='https://github.com/satellogic/calval',
    author_email='amit@satellogic.com',
    description="Python package for easy radiometric calibration&validation of satellite EO payloads",
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],
    packages=find_packages(),
    package_data={
        'calval': ['site_data/*']
    },
    install_requires=install_requires,
    #
    # Hack: no wheel for rasterio 1.0.3 on py3.4,
    # and building from tarball fails...
    extras_require={
        ':python_version == "3.4"': [
            'rasterio<1.0.3'
        ]
    },
    dependency_links=dependency_links
)
