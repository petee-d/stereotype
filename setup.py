import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="stereotype",
    version="1.3.0",
    author="Peter Dolák",
    author_email="peter@dolak.sk",
    description="Models for conversion and validation of rich data structures.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/petee-d/stereotype",
    packages=['stereotype', 'stereotype.fields', 'stereotype.contrib', 'examples'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
