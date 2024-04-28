from setuptools import setup, find_packages

setup(
    name='lipsync_pipeline',
    version='0.0.1',
    description='LipSync Pipeline',
    author='Amadeus (Wasys)',
    packages=find_packages(), 
    install_requires=[],
    Scripts=['lipsync_pipeline/functions.py']
)