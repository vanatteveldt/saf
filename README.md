Python tools for SAF (Simple Annotation Framework)
===

SAF is a light-weight json based representation/annotation framework for NLP data. 
It is designed to be compatible with formats like NAF (newsreader annotation framework) without making too many assumptions.

The general idea is that new annotations add 'layers', which are represented as json dictionary keys. 
Each element in a layer has an id, and other layers can refer to these elements by id. 
Each step in a preprocessing pipeline then adds new layers to the dict, leaving existing layers alone as far as possible.

Note that this is not meant to be a perfect framework, but rather a simple way to deal with NLP data in a json environment.

Contributions for converting to/from other framework and from existing NLP tools are most welcome.

Format specification
====

See [saf.org](saf.org)


