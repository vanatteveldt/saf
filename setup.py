from distutils.core import setup
setup(
version='0.10',
name="saf",
description="Python toolkit for handling Simple Annotation Framework files",
author="Wouter van Atteveldt",
author_email="wouter@vanatteveldt.com",
packages=["saf"],
classifiers=[
"License :: OSI Approved :: MIT License",
],
     install_requires=[
"pygraphviz"
],
)
