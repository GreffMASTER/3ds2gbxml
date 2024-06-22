import logging
import sys
import argparse
import os

from pathlib import Path

import CPlugSurface
import CPlugVisualIndexedTriangles

from CPlugErrors import NoTrimeshError, NoVerticesError, NoFacesError
from modules.threedees import read_3ds, IncorrectFormatError, DataError, EditorChunk, ObjectBlock

VERSION = '1.0.8'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='3ds2gbxml'
    )
    parser.add_argument('file')
    parser.add_argument('-lf', '--logfile',
                        dest='logfile')
    parser.add_argument('-i', '--info',
                        dest='verbose', action='store_true')
    parser.add_argument('-v', '--visual',
                        dest='visual', action='store_true')
    parser.add_argument('-a', '--animate',
                        dest='animate', action='store_true')
    parser.add_argument('-s', '--surface',
                        dest='surface', action='store_true')
    parser.add_argument('--tmf',
                        dest='tmf', action='store_true')

    args = parser.parse_args()

    # Set up logger
    loglevel = logging.WARNING
    if args.verbose:
        loglevel = logging.INFO

    logfile = None
    if args.logfile:
        logfile = args.logfile

    logging.basicConfig(
        level=loglevel,
        format='%(asctime)s-[%(levelname)s]: %(message)s',
        filename=logfile
    )

    logging.info(f'3ds2gbxml version {VERSION}')

    if not args.visual and not args.surface and not args.animate:
        logging.error('Conversion Error: no mode selected')
        sys.exit(1)



    try:
        logging.info('===============================')
        chunk = read_3ds(args.file)

        objects: list = []
        # Find model objects in the file
        for editor_chunk in chunk.children:
            if isinstance(editor_chunk, EditorChunk):
                for obj in editor_chunk.children:
                    if isinstance(obj, ObjectBlock):
                        if len(obj.children) > 0:
                            objects.append(obj)
        if len(objects) == 0:
            logging.error('Conversion Error: no objects to convert')
            sys.exit(1)

        saved_to: list = []
        if args.animate:
            # Add SubVisuals
            try:
                logging.info('===============================')
                gbx_tree = CPlugVisualIndexedTriangles.create_anim_xml(objects)
                print(gbx_tree)
                save_path_file = f"{Path(args.file).stem}.CPlugVisualIndexedTriangles.xml"
                with open(save_path_file, "wb") as f:
                    gbx_tree.write(f)
                    logging.info(f'Saved to "{save_path_file}')
                    saved_to.append(save_path_file)
            except OSError as e:
                logging.error(f'Failed to open "{e.filename}" for writing, message: {e.args[1]}')
                sys.exit(e.errno)
            except NoTrimeshError:
                logging.error('Conversion Error: No mesh present')
                sys.exit(1)
            except NoVerticesError:
                logging.error('Conversion Error: No vertices present')
                sys.exit(1)
            except NoFacesError:
                logging.error('Conversion Error: No faces present')
                sys.exit(1)

        else:
            for model_obj in objects:
                name = model_obj.name.split('$')[0]
                # To Visual Mesh
                if args.visual:
                    try:
                        logging.info('===============================')
                        gbx_tree = CPlugVisualIndexedTriangles.create_xml(model_obj)
                        save_path_file = f"{name}.CPlugVisualIndexedTriangles.xml"
                        with open(save_path_file, "wb") as f:
                            gbx_tree.write(f)
                            logging.info(f'Saved to "{save_path_file}')
                            saved_to.append(save_path_file)
                    except OSError as e:
                        logging.error(f'Failed to open "{e.filename}" for writing, message: {e.args[1]}')
                        sys.exit(e.errno)
                    except NoTrimeshError:
                        logging.error('Conversion Error: No mesh present')
                        sys.exit(1)
                    except NoVerticesError:
                        logging.error('Conversion Error: No vertices present')
                        sys.exit(1)
                    except NoFacesError:
                        logging.error('Conversion Error: No faces present')
                        sys.exit(1)

            # To Collision Surface
            if args.surface:
                try:
                    logging.info('===============================')
                    gbx_tree = CPlugSurface.create_xml(objects, args.tmf)
                    if args.tmf:
                        save_path_file = f"{Path(args.file).stem}.CPlugSurfaceGeom.xml"
                    else:
                        save_path_file = f"{Path(args.file).stem}.CPlugSurfaceCrystal.xml"
                    with open(save_path_file, "wb") as f:
                        gbx_tree.write(f)
                        logging.info(f'Saved to "{save_path_file}')
                        saved_to.append(save_path_file)
                except OSError as e:
                    logging.error(f'Failed to open "{e.filename}" for writing, message: {e.args[1]}')
                    sys.exit(e.errno)
                except NoTrimeshError:
                    logging.error('Conversion Error: No mesh present')
                    sys.exit(1)
                except NoVerticesError:
                    logging.error('Conversion Error: No vertices present')
                    sys.exit(1)
                except NoFacesError:
                    logging.error('Conversion Error: No faces present')
                    sys.exit(1)
    
    except OSError as e:
        logging.error(f'Failed to open "{e.filename}" for reading, message: {e.args[1]}')
        sys.exit(e.errno)
    except IncorrectFormatError:
        logging.error('Parser Error: incorrect 3ds file')
        sys.exit(1)
    except DataError as e:
        logging.error(f'Parser Error: incorrect data at offset: {hex(e.position)}, message: "{e.args[0]}"')
        sys.exit(1)

    logging.info('Done!')
    print(f'Successfully saved the following {len(saved_to)} files:')
    for file_path in saved_to:
        print(file_path)
