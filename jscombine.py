from os.path import join
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--directory', default='base/static/js',
                    help='js directory')
parser.add_argument('-f', '--file', default='config.txt',
                    help='configuration file')
parser.add_argument('-o', '--output', default='rs.js',
                    help='output file')
args = parser.parse_args()

with open(join(args.directory, args.file)) as infile:
    with open(join(args.directory, args.output), 'w') as outfile:
        for line in infile:
            if line:
                component = line.split()[0]
                with open(join(args.directory, component)) as cfile:
                    print >>outfile, '/* file starts: {} */'.format(component)
                    outfile.write(cfile.read())
                    print >>outfile, '/* file ends: {} */'.format(component)
