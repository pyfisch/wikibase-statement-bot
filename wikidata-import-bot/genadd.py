import sys

sys.path.append(r'/home/pyfisch/.pywikibot')
sys.path.append(r'/data/project/pywikipedia/rewrite')

import mainclass

mainobject = mainclass.Main()
template = raw_input("tempate: ")
start = raw_input("start: ")
end = raw_input("end: ")
for i in range(int(start), int(end)):
    catname = template % i
    print catname, mainobject.addTask(catname)

