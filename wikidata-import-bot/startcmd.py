import sys
import time

import pywikibot

sys.path.append(pywikibot.config.base_dir)

import mainclass

statewrapper = {'-2': 'X',
                '-1': 'Q',
                '0': 'E',
                '1': 'R',
                '2': 'S',
                '3': 'W'
                }

taskstatewrapper = {'0': 'W',
                    '1': 'R',
                    '2': 'C'}

def statsprint(mainobject):
    print time.asctime()
    print "%i items of %s waiting." % (len(mainobject.gen), mainobject.fullcatname)
    print "%i items in write buffer." % len(mainobject.buffer)
    print "Threads:| 0 | 1 | 2 | 3 | 4 | 5 | 6 |"
    print "extract | " + " | ".join([statewrapper[str(i['state'])] for i in mainobject.extract_threads])
    print "write   | " + " | ".join([statewrapper[str(i['state'])] for i in mainobject.write_threads])

def main():
    mainobject = mainclass.Main()
    if not '-s' in sys.argv:
        mainobject.startThreads()
    if '-a' in sys.argv:
        automode(mainobject)
    else:
        handmode(mainobject)
    

def automode(mainobject):
    print "Bl"
    while not mainobject.gen_threads[0]['stop']:
        time.sleep(60)
        statsprint(mainobject)
    print "Bla"

def handmode(mainobject):  
    while True:
        text = raw_input("bot> ")
        if text == "end":
            print "Ending bot..."
            mainobject.end()
        elif text == "quit":
            print "Stopping bot..."
            sys.exit()
        elif text == "stats":
            statsprint(mainobject)
        elif text.startswith("tasks"):
            if text == "tasks":
                for i in mainobject.getTasks():
                    print taskstatewrapper[str(i[1])] + '\t' + i[0]
            elif text == "tasks -c":
                for i in mainobject.getTasks(state=2):
                    print taskstatewrapper[str(i[1])] + '\t' + i[0]
            elif text == "tasks -r":
                for i in mainobject.getTasks(state=1):
                    print taskstatewrapper[str(i[1])] + '\t' + i[0]
            elif text == "tasks -w":
                for i in mainobject.getTasks(state=0):
                    print taskstatewrapper[str(i[1])] + '\t' + i[0]
            elif text == "tasks -a":
                while True:
                    catname = raw_input("Enter Category: ")
                    if catname:
                        if not mainobject.addTask(catname):
                            print "Not added."
                    else:
                        break
            elif text == "tasks -d":
                while True:
                    catname = raw_input("Enter Category: ")
                    if catname:
                        mainobject.delTask(catname)
                    else:
                        break
            else:
                print "Unknown param."
        else:
            print "Unknown command."

if __name__ == '__main__':
    main()