# 3ds2gbxml
Convert .3ds model files to GBXML visual and surface model files.

This is a very experimental tool for converting .3ds model files to GBX XML files that can be used to create Solid.Gbx by using the template provided in the repository.  
Created for TrackMania 1.0, but technically works in TMO, TMS and even TMN.  
Requires Python3 and NumPy.

From "HowTo.txt":
```
For use with TM 1.0 only, experimental use only, collisions are unfinished

Here is a template for converting 3ds files to TrackManias Solid files in a form of xml that need to be compiled using `gbxc`
You can find `gbxc` here: https://github.com/GreffMASTER/gbxc
Made for block models

1. Use `3ds2gbxc.py` on your 3ds model: python 3ds2gbxc.py model.3ds -c
2. You will get 2 files for each object in the file, visual mesh and collision mesh
3. Edit the Template.Solid.xml and ModelElements.CPlugTree.xml files and follow the steps there
4. Compile the Template.Solid.xml file with `gbxc`

Tested with blender 2.79 3ds models and plugins for modern blender
Also supports vertex colors (partially) with custom plugin fork: https://github.com/GreffMASTER/blender_export_tmf

To set a surface type for a model object, give it a material with one of these names (case sensitive):
Concrete
Pavement
Grass
Ice
Metal
Sand
Dirt
Turbo
DirtRoad
Rubber
SlidingRubber
Test
Rock
Water
Wood
Danger
Asphalt
WetDirtRoad
WetAsphalt
WetPavement
WetGrass
Snow
```
