from setuptools import setup, find_packages

setup(
    name='lipsync_pipeline',
    version='0.0.4',
    description='LipSync Pipeline',
    author='Amadeus (Wasys)',
    packages=find_packages(), 
    install_requires=[
        'google-cloud-storage',
        'google-api-python-client',
        'Pillow',
        'numpy',
        'moviepy'
    ],
    Scripts=['lipsync_pipeline/functions.py']
)