from setuptools import setup

setup(
    name='emis',
    version='0.2.0',
    packages=['emis'],
    install_requires=[
        'beautifulsoup4',
        'click',
        'pyproj',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'emis=emis.__main__:main',
        ]
    }
)