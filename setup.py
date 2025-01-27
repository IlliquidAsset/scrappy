from setuptools import setup, find_packages

setup(
    name="scrappy",
    version="0.1.0",  # Changed to valid version format
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'flask-cors',
        'flask-sqlalchemy',
        'requests',
        'termcolor',
        'python-dotenv',
        'psycopg2-binary',
        'beautifulsoup4',
        'rapidfuzz',
        'colorama',
        'fastapi',
        'pydantic',
        'uvicorn'
    ]
)