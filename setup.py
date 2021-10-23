from setuptools import setup

setup(
    name='emis',
    version='0.0.1',
    py_modules=['emis'],
    install_requires=[
        'beautifulsoup4',
        'click',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'emis = emis:emis',
        ]
    }
)