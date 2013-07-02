from operator import itemgetter
from collections import defaultdict
import sys,os,csv,getopt
import json

"""
Checksums to Dups

The script processes a tab-delimited checksum manifest and,
for each directory represented counts the number of files and
how many are duplicates.

Note: The script started as an attempt to create the JSON data
needed to feed a TreeMap visualization but was reduced in
scope to this solution to fit time constraints.

"""


# Splits a path into an array of directories composing the path
def splitpatharray(path):
    folders=[]
    while 1:
        path,folder = os.path.split(path)
        if folder != "":
            folders.append(folder)
        else:
            if path != "":
                folders.append(path)
            break
    folders.reverse()
    return folders


# Generic node tree builder
def buildnodepath(treenode, path, dup):
    current_dir = path.pop(0)
    if 'path' not in treenode: #First run
        treenode['path'] = ''
    # Find/create the node
    next_node = None
    try:
        next_node = next((item for item in treenode['children'] if item['name'] == current_dir),None)
        if next_node == None:
            next_node = {'name':current_dir,
                         'path': os.sep.join([treenode['path'],current_dir])}
            if len(path) > 1: #dir contains files or subdirectories
                next_node['children'] = list()
                next_node['size'] = int()
                next_node['dup_count'] = int()
            treenode['children'].append(next_node)
        # Use case 1: If there are more nodes (dirs OR files)
        if len(path) > 0:
            try:
                next_node['size'] = next_node['size'] + 1
            except:
                next_node['size'] = 1
            if dup:
                try:
                    next_node['dup_count'] = next_node['dup_count'] + 1
                except:
                    next_node['dup_count'] = 1
            buildnodepath(next_node, path, dup)
        elif len(path) == 0:
            next_node['duped'] = dup
    except:
        pass

# loads the checksum manifest, identifies dups, and kicks off tree creation
def buildtree(checksum_file):
    checksums = defaultdict(list)
    dirtree = {'children':list(),'name':'root'}

    # Load checksum list
    file = open(checksum_file, "r")
    for line in file.readlines():
        try:
            checksum,path = line.strip().split('\t',2)
            checksums[checksum].append(path)
        except:
            pass
        
    # Look for dups
    paths = {}
    for checksum,check_paths in checksums.items():
        are_dups = False
        if len(check_paths) > 1:
            are_dups = True

        for path in check_paths:
            paths[path] = are_dups
    paths = sorted(paths.items(), key=itemgetter(1), reverse=True)

    #build structure from sorted paths
    for pathdup_arr in paths:
        path = splitpatharray(pathdup_arr[0])
        buildnodepath(dirtree, path, pathdup_arr[1])

    return dirtree

# Encodes a node tree into JSON
def encode(tree, out_file_path='tree.json'):
    json_out = open(out_file_path, 'wb')
    json_out.write(bytes(json.dumps(tree,sort_keys=True,indent=4, separators=(',', ': ')),'UTF-8'))
    json_out.close()

# Prints out node tree as CSV
def printtree(tree, out_file='tree.csv'):
    out = csv.writer(open(out_file,'w',newline=''),delimiter=',',quoting=csv.QUOTE_MINIMAL)
    out.writerow(['path','file_count','duplication_count'])
    tree2csv(tree,out)
    
# Tree2CSV recursion
def tree2csv(tree,out):
    # Write out a directory
    try:
        if 'duped' not in tree: #Excludes leaf (file) nodes
            path = tree['path']
            counts = tree['size']
            dups = tree['dup_count']
            out.writerow([path,str(counts),str(dups)])
    except:
        pass
    #Recuse children
    if 'children' in tree:
        for child in tree['children']:
            tree2csv(child,out)

def main():
    try:          
        opts, args = getopt.getopt(sys.argv[1:], "hc:j:", ["help","csv","json"]) 
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    csv = None
    json = None
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        if opt in ('-c','--csv'):
            csv = arg
        if opt in ('-j','--json'):
            json = arg
    if csv is None and json is None:
        print("Please select CSV, JSON, or both.")
        usage()
        sys.exit(2)

    # process input file
    for arg in args:
        if os.path.isfile(arg):
            tree = None
            try:
                print("Building tree...")
                tree = buildtree(arg)
                if json:
                    print("Exporting JSON to %s" % (json))
                    encode(tree,json)
                if csv:
                    print("Exporting CSV to %s" % (csv))
                    printtree(tree,csv)
            except:
                print("Could not process %s; unkown reason." % (arg))
                usage()
                sys.exit(2)
        else:
            print("Could not process %s; it isn't a file." % (arg))
            usage()
            sys.exit(2)

def usage():
    text = """checksums2dups - creates list of directories with duplicated file counts
from tab-delimintated checksum manifests.

checksums2dups [c,j output] manifest

-c --csv output_file\tCreates a CSV file
-j --json output file\tCreates a JSON file

At least one output (CSV or JSON) must be selected.

Example: python checksums2dups -c dups.csv manifest.tab
Takes the "manifest.tab" checksum manifest and creates a dup CSV list in "dups.csv".
"""
    print(text)

if __name__ == "__main__":
    main()
