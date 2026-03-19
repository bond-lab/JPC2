

Thesaurus: <https://www.benjamins.com/catalog/hcp.78/additional?srsltid=AfmBOopB3gK0syUJ-UkQeCyRQJIm2U68doaRRkoJxkUBxR5oG532a7YB>

Use the python wn module: https://pypi.org/project/wn/

e.g.
```
Python 3.13.2 (main, Feb 12 2025, 14:51:17) [Clang 19.1.6 ] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import wn
>>> ewn = wn.Wordnet('omw-en:2.0')
>>> ewn.synsets('amber')
[Synset('omw-en-04966240-n'), Synset('omw-en-14894880-n'), Synset('omw-en-00369504-s')]
>>> ewn.synsets('amber')[0].definition()
'a deep yellow color'
>>> ewn.synsets('amber')[0].lemmas()
['amber', 'gold']
>>> ewn.synsets('amber')[0].hypernym_paths()
[[Synset('omw-en-04965661-n'), Synset('omw-en-04959672-n'), Synset('omw-en-04956594-n'), Synset('omw-en-04950126-n'), Synset('omw-en-04916342-n'), Synset('omw-en-00024264-n'), Synset('omw-en-00002137-n'), Synset('omw-en-00001740-n')]]
>>> f
Traceback (most recent call last):
  File "<python-input-7>", line 1, in <module>
    f
NameError: name 'f' is not defined
>>> for ss in ewn.synsets('amber')[0].hypernym_paths()[0]:
...     print(ss.lemmas())
...     
['yellow', 'yellowness']
['chromatic color', 'chromatic colour', 'spectral color', 'spectral colour']
['color', 'colour', 'coloring', 'colouring']
['visual property']
['property']
['attribute']
['abstraction', 'abstract entity']
['entity']
>>> for ss in ewn.synsets('amber')[1].hypernym_paths()[0]:
...     print(ss.lemmas())
...     
['natural resin']
['resin', 'rosin']
['organic compound']
['compound', 'chemical compound']
['chemical', 'chemical substance']
['material', 'stuff']
['substance']
['matter']
['physical entity']
['entity']
>>> for ss in ewn.synsets('emerald')[1].hypernym_paths()[0]:
...     print(ss.lemmas())
...     
['jewel', 'gem', 'precious stone']
['jewelry', 'jewellery']
['adornment']
['decoration', 'ornament', 'ornamentation']
['artifact', 'artefact']
['whole', 'unit']
['object', 'physical object']
['physical entity']
['entity']
>>> for ss in ewn.synsets('emerald')[2].hypernym_paths()[0]:
...     print(ss.lemmas())
...     
['green', 'greenness', 'viridity']
['chromatic color', 'chromatic colour', 'spectral color', 'spectral colour']
['color', 'colour', 'coloring', 'colouring']
['visual property']
['property']
['attribute']
['abstraction', 'abstract entity']
['entity']
>>> for ss in ewn.synsets('emerald')[0].hypernym_paths()[0]:
...     print(ss.lemmas())
...     
['beryl']
['mineral']
['material', 'stuff']
['substance']
['matter']
['physical entity']
['entity']
```
