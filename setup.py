from setuptools import setup

setup(
    name = "Nexus Manager",
    version = "0.0.3",
    description = "Sonatype Nexus Raw repositories manager",
    author = "therealmal",
    author_email = "therealmal23@gmail.com",
    entry_points = {
        "console_scripts": [
            "nexmanager = main:main"
        ]
    }
)