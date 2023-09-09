import logging
import sys
import argparse

import CPlugSurface
import CPlugVisualIndexedTriangles

from CPlugErrors import NoTrimeshError, NoVerticesError, NoFacesError
from modules.threedees import read_3ds, IncorrectFormatError, DataError, EditorChunk, ObjectBlock

VERSION = '1.0.3'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='3ds2gbxml'
    )
    parser.add_argument('3ds-file')
    parser.add_argument('-lf', '--logfile',
                        dest='logfile')
    parser.add_argument('-v', '--verbose',
                        dest='verbose', action='store_true')
    parser.add_argument('-c', '--collision',
                        dest='collision', action='store_true')
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

    try:
        logging.info('===============================')
        chunk = read_3ds(sys.argv[1])

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

        for model_obj in objects:
            name = model_obj.name.split('$')[0]

            # To Visual Mesh
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

            # To Collision Surface (wip)
            if args.collision:
                try:
                    logging.info('===============================')
                    gbx_tree = CPlugSurface.create_xml(model_obj)
                    save_path_file = f"{name}.CPlugSurface.xml"
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
