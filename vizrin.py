# coding=utf-8
# ----------------------------------------------------
# Agnieszka Pogorzelska
# VIZRIN

# ----------------------------------------------------
__author__ = 'Agnieszka Pogorzelska'

import os
import datetime
import sys
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
from PySide import QtGui,QtCore
import pyqtgraph
import pandas
from pandasqt.models.DataFrameModel import DataFrameModel
import numpy

reload(sys)
sys.setdefaultencoding('utf8')


def str2datetime(inputstr):
    """ Converts datetime converted to string back into datetime. Supports both version with miliseconds and without.
    """
    try:
        return datetime.datetime.strptime(inputstr, "%Y-%m-%d %H:%M:%S.%f")
    except:
        return datetime.datetime.strptime(inputstr, "%Y-%m-%d %H:%M:%S")

def str2float(string):
    """ Converts number string of observation into float number
    """
    if string.strip() != "":
        number = float(string[:-4])
        number *= 10**(int(string[-3:]))
        return number
    else:
        return numpy.nan

def epochs2hours(list):
    """ Converts a list of epochs in datetime format to hours starting from the first epoch
    """
    list = [element-list[0] for element in list]
    list = [element.total_seconds()/3600 for element in list]
    return list

def filterPanelByList(panel,axis,filter=[]):
    """ Filters Pandas object (panel or dataframe) based on a given list of labels and axis
    """
    #uwaga: ta wersja bierze labels w domyślnym typie, getlabellist bierze labels jako listę stringów
    if axis == 'minor_axis':
        #labels = GetLabelList(panel, "minor_axis")
        labels = panel.minor_axis.tolist()
        panel = panel.swapaxes("items", "minor_axis")
    elif axis == 'major_axis':
        #labels = GetLabelList(panel, "major_axis")
        labels = panel.major_axis.tolist()
        panel = panel.swapaxes("items", "major_axis")
    else:
        #labels = GetLabelList(panel, "items")
        labels = panel.items.tolist()

    if not filter == []:
        try:
            labels = [label for label in labels if label in filter]
            panel = panel.loc[labels]
        except Exception:
            print(sys.exc_info()[1])

    if axis == 'minor_axis':
        panel = panel.swapaxes("minor_axis","items")
    elif axis == 'major_axis':
        panel = panel.swapaxes("major_axis","items")

    return panel

def GetLabelList(pandasitem, axis):
    """ Function returning list of labels (as strings) on given [axis] from panel/dataframe
    """
    if axis == 'items':
        return [str(element) for element in pandasitem.items.tolist()]
    elif axis == 'major_axis':
        return [str(element) for element in pandasitem.major_axis.tolist()]
    elif axis == 'minor_axis':
        return [str(element) for element in pandasitem.minor_axis.tolist()]
    elif axis == 'columns':
        return [str(element) for element in pandasitem.columns.tolist()]
    elif axis == 'index':
        return [str(element) for element in pandasitem.index.tolist()]

def Panel2DataFrame(panel, axis, label):
    """ Pulls out a dataframe from a pandas panel based on a given axis and label (filter)
    """
    if axis == 'items':
        return panel[label]
    elif axis == 'major_axis':
        panel = panel.swapaxes("items", "major_axis")
        return panel[label]
    elif axis == 'minor_axis':
        panel = panel.swapaxes("items", "minor_axis")
        panel = panel.swapaxes("minor_axis", "major_axis")
        return panel[label]

class RinexFile(object):

    def CheckPath(self,path,ext):
        """ Checks if the file on a given "path" exists and has the right extension ("ext")
        """
        #Sprawdzenie czy plik istnieje
        if not os.path.isfile(os.path.abspath(path)):
            raise ValueError("Plik nie istnieje")

        # Sprawdzenie rozszerzenie pliku
        # (To pierwsze -1 mogłoby równie dobrze być jako 1, bo chodzi nam o drugi element tupli,
        # który jest jednocześnie ostatnim)
        # TODO Nie jestem pewna czy abspath jest w tym przypadku konieczne. Sprawdzić gdy będzie pyside. Consider using basename and expanduser
        if not os.path.splitext(os.path.basename(path))[-1][-1].lower() == ext:
            raise ValueError("Plik nie posiada poprawnego rozszerzenia. Rozszerzenie powinno być "+str(ext)+" a jest "+os.path.splitext(os.path.basename(path))[-1][-1].lower())

    def ReadIDs(self,path):
        """ Reads File ID ("fid") and Station ID ("sid") from file name
        """
        # todo Odczytanie informacji z nazwy pliku: 4-znakowe ID stacji, dzień roku, numer sekwencji (lub numer godziny/minut - co 15)
        self.fid = os.path.splitext(os.path.basename(path))[0]
        self.sid = os.path.splitext(os.path.basename(path))[0][:4]

    def GetLabelList(self,pandasitem,axis):
        """ Function returning list of labels on given [axis] from panel/dataframe
        """
        if axis == 'items':
            return [str(element) for element in pandasitem.items.tolist()]
        elif axis == 'major_axis':
            return [str(element) for element in pandasitem.major_axis.tolist()]
        elif axis == 'minor_axis':
            return [str(element) for element in pandasitem.minor_axis.tolist()]
        elif axis == 'columns':
            return [str(element) for element in pandasitem.columns.tolist()]
        elif axis == 'index':
            return [str(element) for element in pandasitem.index.tolist()]

class ObsFile(RinexFile):
    """Plik obserwacyjny"""

    def __init__(self, path):
        """ Tworzy obiekt klasy ObsFile na podstawie pliku ASCII w formacie RINEX
        """

        #self.CheckPath(path,'o')
        self.ReadIDs(path)

        #Zapisanie nazwy pliku i ścieżki
        self.filename = os.path.splitext(os.path.basename(path))[0]
        self.filepath = path

        #Zainicjowanie słownika z którego ostatecznie utworzony będzie pandas panel
        #do słownika dodawane będą pandas DataFrame z których każda to rekord, czas jest kluczem
        obsdict = {}
        typeslist = []

        #Otworzenie pliku
        print "----------------------------------------------------------------------------------------------------"
        print "Otworzono plik obserwacyjny " + os.path.basename(path)
        print "----------------------------------------------------------------------------------------------------"

        with open(path, "r+") as rinexfile:

            insideheader = True


            for line in rinexfile:

                if insideheader == True:
                    if "END OF HEADER" in line[60:79]:
                        insideheader = False
                        print "Zakończono odczytywanie nagłówka"
                        print
                    elif "# / TYPES OF OBSERV" in line[60:79]:
                        typeslist += line[6:60].split()
                        print "W pliku obserwacyjnym znajduje sie " + str(len(typeslist)) + " typów obserwacji: "+str(typeslist)

                else:
                    print "------------------START OF RECORD"

                    #Pozyskaj czas
                    timel = line[1:26].split()
                    print "Time list read from line= "+str(timel)
                    # mikrosekundy
                    timel.append(timel[-1][-7:-1])
                    # sekundy
                    timel[-2] = timel[-2][:-8]

                    timel = [int(el) if el != "" else 0 for el in timel]

                    # rok
                    if timel[0] < 80:  timel[0] += 2000
                    else: timel[0] += 1900
                    # convert to datetime format
                    recordtime = datetime.datetime(*timel) #Konieczne bo potem niestety skipuje
                    # delete no longer needed list
                    del timel
                    print "Odczytano czas w nagłówku rekordu: " + str(recordtime)

                    satlist = self.getsatlist(line,rinexfile)
                    print "Odczytano listę satelitów w nagłówku rekordu: " + str(satlist)
                    print

                    print "-----STARTING FOR LOOP"
                    #Zainicjowanie słownika do którego będą zapisywane obserwacje z pojedynczego rekordu
                    #Numer satelity jest kluczem

                    recorddict = {}

                    line = rinexfile.next()
                    s = 0
                    for sat in satlist:
                        s += 1

                        n = 14 #dlugosc odleglosci w znakach
                        m = 16 #co ile skacze poczatek odl w znakach
                        #obslist = [float(j) for j in [line[i:i + n] for i in range(0, 81, m)] if j not in ['\n', '']]
                        # W ten sam sposob moznaby odczytac LLI i SSI

                        #obslist = [float(j) for j in [line[i:i + n] for i in range(0, 81, m)] if j.strip() not in ['\n', '']] #uwzglednic puste miejsca

                        #obslist = [float(j) if j.strip() not in ['\n', ''] else numpy.nan for j in [line[i:i + n] for i in range(0, 81, m)] ]
                        obslist = []
                        for j in [line[i:i + n] for i in range(0, 81, m)]:
                            #print [j]
                            if j.strip() not in ['\n', '']:
                                obslist.append(float(j))
                            elif j not in ['\n','']:
                                obslist.append(numpy.nan)

                        for x in range(0,int(float(len(typeslist)) / 5.0 - 0.1)):
                            try:
                                line = rinexfile.next()
                                #obslist += [float(j) for j in [line[i:i + n] for i in range(0, 81, m)] if j.strip() not in ['\n', '']] #uwzglednic puste miejsca
                                #obslist += [float(j) if j.strip() not in ['\n', ''] else numpy.nan for j in [line[i:i + n] for i in range(0, 81, m)] ]
                                for j in [line[i:i + n] for i in range(0, 81, m)]:
                                    #print [j]
                                    if j.strip() not in ['\n','']:
                                        obslist.append(float(j))
                                    elif j not in ['\n','']:
                                        obslist.append(numpy.nan)
                            except:
                                pass
                        print "Odczytano rekord satelity " + sat + "  " + str(obslist)

                        #Przekonwertowanie listy do słownika1 (z typem obs jako kluczem) i dodanie do słownika2 z ID satelity jako kluczem
                        recorddict[sat] = dict(zip(typeslist, obslist))

                        if s<len(satlist): line = rinexfile.next()

                    print "-----ENDING FOR LOOP\n"

                    #Dodanie slownika2 do słownika3, z czasem jako kluczem
                    obsdict[recordtime] = recorddict
                    print "Dodano pozycję do słownika, z kluczem: " + str(recordtime)
                    print "------------------END OF RECORD\n\n"

                    #Usunięcie niepotrzebnego słownika
                    del recorddict

        self.obspanel = pandas.Panel.from_dict(obsdict, intersect=False, orient='items', dtype=None)
        self.obspanel = self.obspanel.swapaxes('major_axis','minor_axis')

        print "Zapisano "+str(len(obsdict))+" rekordy do panelu pandas"
        print "Osie utworzonego panelu pandas: "
        print self.obspanel.axes
        print
        del obsdict

        print "----------------------------------------------------------------------------------------------------"
        print "Zamknięto plik obserwacyjny " + str(path)
        print "----------------------------------------------------------------------------------------------------\n"
        #--------------------------------------------------------------------------------------------------

            # TODO Dodac sprawdzenie wersji pliku RINEX

    def GetMultipath(self,satellite,f1,f2,pr1,pr2,k=3):
        """ Calculates multipath mp1 and mp2 for a [satellite] and given phase ([f1],[f2]) and pseudorange ([pr1],[pr2])
        observations. GLonass satellites use given frequency channel [k] to calculate frequency.
        """
        panel = self.obspanel
        df =  Panel2DataFrame(panel,"major_axis",satellite)

        if "E" in satellite:
            frequencies = {"1":1575.42,"5":1176.45,"6":1278.75,"7":1207.140,"8":1191.795}
        elif "R" in satellite:
            frequencies = {"1":1602.00+float(k)*9.0/16.0, "2":1246.00+float(k)*7.0/16.0}
        else:
            frequencies = {"1":1575.42,"2":1227.60,"5":1176.45}

        alfa = frequencies[f1[-1]]**2/frequencies[f2[-1]]**2

        # Calculate multipath if all the measurements used in formula are not 0 (prevents wrong values being calculated)
        df['mp1'] = df.apply(lambda row: (row[pr1] - row[f1] - 2/(alfa-1) * (row[f1]-row[f2]))
                                                        if ((str(row[f1])!="0.0") & (str(row[f2])!="0.0") & (str(row[pr1])!="0.0") & (str(row[pr2])!="0.0"))
                                                        else numpy.nan,
                                                        axis=1
                             )
        df['mp2'] = df.apply(lambda row: (row[pr2] - row[f2] - 2 / (alfa - 1) * (row[f1] - row[f2]))
                                                        if ((str(row[f1]) != "0.0") & (str(row[f2]) != "0.0") & (str(row[pr1]) != "0.0") & (str(row[pr2]) != "0.0"))
                                                        else numpy.nan,
                                                        axis=1
                             )

        return df[["mp1","mp2"]]

    def GetPanel(self):
        return self.obspanel

    def GetSatellites(self):
        """ Returns a list of satellites contained in obspanel
        """
        return self.GetLabelList(self.obspanel, 'major_axis')

    def GetObsTypes(self):
        """ Returns a list of observation types contained in obspanel
            """
        return self.GetLabelList(self.obspanel, 'minor_axis')

    def GetEpochs(self):
        """ Returns a list of epochs contained in obspanel
            """
        return self.GetLabelList(self.obspanel, 'items')

    def getsatlist(self, line, rinexfile):
        """ Reads a list of satellites from a given line in a rinex file. Used during parsing of rinex file.
        """
        # Utwórz listę satelitów z linii pliku
        n = 3
        satlist = [j for j in [line[i:i + n] for i in range(32, 68, n)] if j.strip() != '' and j.strip() != '\n']
        print "Odczytano liczbę satelit: " + line[30:32]
        if int(line[30:32]) > 12 and int(line[30:32]) <= 24:
            print "Wykryto 2 linie dla satelit. Odczytuję satelity"
            # Przeskocz do następnej linii
            line = next(rinexfile)
            satlist += [j for j in [line[i:i + n] for i in range(32, 68, n)] if j.strip() != '' and j.strip() != '\n']

        elif int(line[30:32]) > 24:
            print "Wykryto 3 linie dla satelit. Odczytuję satelity"
            # Przeskocz do następnej linii
            line = next(rinexfile)
            satlist += [j for j in [line[i:i + n] for i in range(32, 68, n)] if j.strip() != '' and j.strip() != '\n']
            line = next(rinexfile)
            satlist += [j for j in [line[i:i + n] for i in range(32, 68, n)] if j.strip() != '' and j.strip() != '\n']

        else: print "Wykryto 1 linię dla satelit. Odczytuję satelity"

        return satlist

class NavFile(RinexFile):
    """Plik nawigacyjny"""

    def __init__(self, path):



        #self.CheckPath(path,'n')
        self.ReadIDs(path)

        #Zapisanie nazwy pliku i ścieżki
        self.filename = os.path.splitext(os.path.basename(path))[0]
        self.filepath = path

        #todo dodac sprawdzenie typu rinexa obs (czy gps czy inny)

        # Otworzenie pliku
        print "----------------------------------------------------------------------------------------------------"
        print "Otworzono plik nawigacyjny " + os.path.basename(path)
        print "----------------------------------------------------------------------------------------------------"

        linenum = 0
        listparam = []
        masterlistparam = []

        with open(path, "r+") as rinexfile:

            insideheader = True
            self.recordlines = 7
            paramtypes = ["SV clock bias [s]", "SV clock drift [s/s2]", "SV clock drift rate [s/s2]",
                          "IODE Issue of Data, Ephemeris", "Crs [m]", "Delta n [rad/s]", "M0 [rad]",
                          "Cuc [rad]", "e Eccentricity", "Cus [rad]", "sqrt(A) [m^1/2]",
                          "Toe Time of Ephemeris [s of gps week]", "Cic [rad]", "OMEGA [rad]", "CIS [rad]",
                          "i0 [rad]", "Crc [m]", "omega [rad]", "OMEGA DOT [rad/s]",
                          "IDOT [rad/s]", "Codes on L2 channel", "GPS Week #", "L2 P data flag",
                          "SV accuracy [m]", "SV health", "TGD [m]", "IODC Issue of Data, Clock",
                          "Transmission time of message [s of gps week]", "Fit interval [h]", "extra field 1",
                          "extra field 2"
                          ]
            self.navfiletype = "GPS"

            for line in rinexfile:

                if insideheader == True:
                    if "END OF HEADER" in line[60:79]:
                        insideheader = False
                        print "Zakończono odczytywanie nagłówka"
                        print

                    elif "DELTA-UTC" in line[60:79]:
                        self.gpsday = int(line[51:59].split()[-1])
                        print "Odczytany numer dnia gps: " + str(self.gpsday)
                        self.gpsweek = int(line[42:50].split()[-1])
                        print "Odczytany numer tygodnia gps: " + str(self.gpsweek)

                    elif "GLONASS" in line[0:80]:
                        print "Detected GLONASS file"
                        self.navfiletype = "GLONASS"
                        paramtypes = ["SV clock bias [s]","SV Relative Frequency Bias","Message Frame Time [s/s2]",
                                          "Satellite X Position [km]","Satellite X Velocity [km/s]",
                                          "Satellite X Acceleration [km/s2]","Satellite Health",
                                          "Satellite Y Position [km]","Satellite Y Velocity [km/s]",
                                          "Satellite Y Acceleration [km/s2]","Frequency Number",
                                          "Satellite Z Position [km]","Satellite Z Velocity [km/s]",
                                          "Satellite Z Acceleration [km/s2]","Information Age [days]"
                                      ]
                        self.recordlines = 3

                else:

                    if linenum == 0:
                        print str(linenum)+"/"+str(self.recordlines)
                        print str(line)

                        if int(line[2:5]) < 80:
                            year = 2000 + int(line[2:5])
                        else:
                            year = 1900 + int(line[2:5])

                        epoch = datetime.datetime(year, int(line[5:8]), int(line[8:11]), int(line[11:14]),
                                                int(line[14:17]), int(line[17:20]), int(float(line[21:22]) * 1000000))

                        print "Odczytano epokę: "+str(epoch)

                        listparam+=[
                            int(line[0:2]),
                            epoch,
                            str2float(line[22:41]),
                            str2float(line[41:60]),
                            str2float(line[60:79])
                        ]

                        linenum += 1

                    elif linenum < self.recordlines and linenum != 0:
                        print linenum
                        print str(line)
                        listparam+=[
                            str2float(line[0:22]),
                            str2float(line[22:41]),
                            str2float(line[41:60]),
                            str2float(line[60:79])
                        ]
                        linenum += 1

                    else:
                        print linenum
                        linenum = 0
                        print str(line)
                        listparam+=[
                            str2float(line[0:22]),
                            str2float(line[22:41]),
                            str2float(line[41:60]),
                            str2float(line[60:79])
                        ]
                        print "last line in block - block list:"
                        print listparam
                        print "appending blocklist to masterlist"
                        masterlistparam.append(listparam)
                        print "clearing listparam"
                        listparam = []

        print "----------------------------------------------------------------------------------------------------"
        print "Zamknięto plik nawigacyjny " + str(path)
        print "----------------------------------------------------------------------------------------------------\n"

        print "masterlist:"
        print masterlistparam
        epochs = [listparam[1] for listparam in masterlistparam]
        epochs = sorted(list(set(epochs)))
        navdict = {}
        for epoch in epochs:
            print "Sortowanie po epoce "+str(epoch)
            epochlistparam = [listparam[2:] for listparam in masterlistparam if listparam[1]==epoch]
            epochlistsat = [listparam[0] for listparam in masterlistparam if listparam[1]==epoch]
            print "Uzyskano dane: "+str(epochlistparam)
            print "Uzyskano satelity: "+str(epochlistsat)
            df = pandas.DataFrame(epochlistparam,epochlistsat,paramtypes)
            print "Utworzono DataFrame: "
            print df
            navdict[epoch]=df
        print "Utworzono dictionary dataframes"
        print "Usuwanie duplikatow w slowniku"
        #drop duplicates in every dataframe
        for k, v in navdict.iteritems():
                print "Epoka "+str(k)
                print "    Przed usunieciem duplikatow:"
                print list(navdict[k].index)
                #Usuniecie zduplikowanych danych dla danej kombinacji epoka+satelita
                v = v.drop_duplicates()
                #v['index1'] = v.index
                v = v.groupby(level=0).last()
                #v = v.drop('index1', 1)
                navdict[k] = v
                print "    Po usunieciu duplikatow"
                print list(navdict[k].index)
                print navdict[k]
                #pass

        print "Przekształcanie do panelu"

        self.navpanel = pandas.Panel.from_dict(navdict, intersect=False, orient='items', dtype=None)
        print self.navpanel

    def GetPanel(self):
        return self.navpanel

    def GetSatellites(self):
        """ Returns a list of satellites contained in navpanel
        """
        return self.GetLabelList(self.navpanel, 'major_axis')

    def GetParameters(self):
        """ Returns a list of parameters contained in navpanel
        """
        return self.GetLabelList(self.navpanel,'minor_axis')

    def GetEpochs(self):
        """ Returns a list of epochs contained in navpanel
        """
        return self.GetLabelList(self.navpanel,'items')

class MainWindow(QtGui.QMainWindow):
    """ Main Window class
    """
    def __init__(self):
        """ Constructor Function
        """
        super(MainWindow,self).__init__()
        self.initGUI()

    def initGUI(self):
        # Enable pyqtgraph antialiasing for prettier plots
        pyqtgraph.setConfigOptions(antialias=True)
        #Change default colors of plots
        pyqtgraph.setConfigOption('background', 'w')
        pyqtgraph.setConfigOption('foreground', 'k')

        # Setup and draw main application window
        self.setWindowTitle("Vizrin | Agnieszka Pogorzelska")
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        self.setGeometry(300, 250, 800, 500)
        self.center()
        QtGui.QToolTip.setFont(QtGui.QFont("Decorative", 8, QtGui.QFont.Bold))
        self.SetupComponents()
        self.show()

    def SetupComponents(self):
        """ Function to setup status bar, central widget, menu bar
        """
        self.myStatusBar = QtGui.QStatusBar()
        self.setStatusBar(self.myStatusBar)

        self.SetButtons()

        self.CreateActions()
        self.CreateMenus()
        self.helpMenu.addAction(self.aboutAction)
        self.helpMenu.addAction(self.aboutQtAction)
        self.helpMenu.addSeparator()
        self.helpMenu.addAction(self.exitAction)

        self.CreateFileTab()
        self.CreateNavPlotTab()
        self.CreateObsPlotTab()
        self.CreateTabs()
        self.setCentralWidget(self.tabs)


    #---------------------------------------------
    # Main window tabs
    #---------------------------------------------

    def CreateTabs(self):
        """ Function to create tabs
        """
        self.tabs = QtGui.QTabWidget()
        self.tabs.addTab(self.fileTab, "Rinex file")
        self.tabs.addTab(self.navPlotTab, "Orbit parameter plot")
        self.tabs.addTab(self.obsPlotTab, "Multipath plot")

    def CreateFileTab(self):

        self.CreateRinexTable()
        self.CreateRinexTableSettings()
        self.CreateRinexTableName()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.rinexTableSettings)
        layout.addWidget(self.rinexTable)
        layout.addWidget(self.rinexTableName)

        self.fileTab = QtGui.QWidget()
        self.fileTab.setLayout(layout)

    def CreateObsPlotTab(self):
        """ Function to create a widget obsPlotTab containing a plot of multipath and its settings
        """
        self.CreateObsPlot()
        self.CreateObsPlotSettings()
        self.CreateObsPlotName()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.obsPlotSettings)
        layout.addWidget(self.obsPlot)
        layout.addWidget(self.obsPlotName)

        self.obsPlotTab = QtGui.QWidget()
        self.obsPlotTab.setLayout(layout)

    def CreateNavPlotTab(self):
        """ Function to create a widget navPlotTab containing a plot of orbital parameters and its settings
        """
        self.CreateNavPlot()
        self.CreateNavPlotSettings()
        self.CreateNavPlotName()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.navPlotSettings)
        layout.addWidget(self.navPlot)
        layout.addWidget(self.navPlotName)

        self.navPlotTab = QtGui.QWidget()
        self.navPlotTab.setLayout(layout)


    #---------------------------------------------
    # Plot/table and plot/table settings
    #---------------------------------------------


    def CreateRinexTableName(self):
        """ Function to create a widget displaying file name
        """
        self.rinexTableName = QtGui.QLabel()

    def CreateRinexTable(self):
        """ Initiates a table view of a dataframe
        """
        self.rinexTable = QtGui.QTableView()
        self.clearTable()

    def CreateRinexTableSettings(self):
        self.rinexTableSettings = QtGui.QWidget()
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.fileButton)
        layout.addWidget(self.clearTableButton)
        layout.addWidget(self.drawTableButton)
        layout.addWidget(self.chooseTableSetting)
        layout.addWidget(self.chooseTableSetting2)
        self.rinexTableSettings.setLayout(layout)


    def CreateNavPlotName(self):
        """ Function to create a widget displaying file name
        """
        self.navPlotName = QtGui.QLabel()

    def CreateNavPlot(self):
        """ Function to create an empty plot of orbit parameter and a widget navPlot that contains it
        """
        #Create plot widget
        self.navPlot = pyqtgraph.PlotWidget(name='NavPlot')
        #Hide elements of the default plot
        self.navPlot.showAxis("bottom",False)
        self.navPlot.showAxis("left", False)
        self.navPlot.showGrid(False,False,0.0)
        #Enable automatic scaling of the plot
        self.navPlot.enableAutoScale()
        #Show autoscale button (doesnt seem to be working???)
        self.navPlot.showButtons()
        #Disable plot
        self.navPlot.setEnabled(False)

    def CreateNavPlotSettings(self):
        """ Function to create a widget with settings affecting the orbit parameters plot contained in navPlot
        """
        # Create widget
        self.navPlotSettings = QtGui.QWidget()
        # Create layout
        layout = QtGui.QHBoxLayout()
        # Add elements to layout
        layout.addWidget(self.navFileButton)
        layout.addWidget(self.clearNavPlotButton)
        layout.addWidget(self.drawNavPlotButton)

        label = QtGui.QLabel("Parameter:")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)

        layout.addWidget(self.chooseNavParam)

        label = QtGui.QLabel("Satellite:")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)

        layout.addWidget(self.chooseNavSat)

        self.navPlotSettings.setLayout(layout)


    def CreateObsPlotName(self):
        """ Function to create a widget displaying file name
        """
        self.obsPlotName = QtGui.QLabel()

    def CreateObsPlot(self):
        """ Function to create an empty plot of multipath and a widget obsPlot that contains it
        """
        # Create plot widget
        self.obsPlot = pyqtgraph.PlotWidget(name='ObsPlot')
        #Hide elements of the default plot
        self.obsPlot.showAxis("bottom",False)
        self.obsPlot.showAxis("left", False)
        self.obsPlot.showGrid(False,False,0.0)
        #Enable automatic scaling of the plot
        self.obsPlot.enableAutoScale()
        #Show autoscale button (doesnt seem to be working???)
        self.obsPlot.showButtons()
        #Disable plot
        self.obsPlot.setEnabled(False)

    def CreateObsPlotSettings(self):
        """ Function to create a widget with settings affecting the multipath plot contained in a widget obsPlot
        """
        #Create widget
        self.obsPlotSettings = QtGui.QWidget()
        #Create layout
        layout = QtGui.QHBoxLayout()
        #Add elements to layout
        layout.addWidget(self.obsFileButton)
        layout.addWidget(self.clearObsPlotButton)
        layout.addWidget(self.drawObsPlotButton)
        label = QtGui.QLabel("Satellite:")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(self.chooseObsSat)
        label = QtGui.QLabel("Frequency Channel:")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(self.freqChannel)
        label = QtGui.QLabel("Frequency 1:")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(self.chooseObsFreq1)
        label = QtGui.QLabel("Pseudorange 1:")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(self.chooseObsPseudor1)
        label = QtGui.QLabel("Frequency 2:")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(self.chooseObsFreq2)
        label = QtGui.QLabel("Pseudorange 2:")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(self.chooseObsPseudor2)
        #Apply layout to widget
        self.obsPlotSettings.setLayout(layout)


    #---------------------------------------------
    # Menus, actions, buttons
    #---------------------------------------------

    def SetButtons(self):
        """ Function to create buttons
        """
        #Create button widgets
        self.navFileButton = QtGui.QPushButton('Open Nav Rinex File')
        self.obsFileButton = QtGui.QPushButton('Open Obs Rinex File')
        self.fileButton = QtGui.QPushButton('Open Rinex File')
        self.clearTableButton = QtGui.QPushButton('Clear Table')
        self.clearNavPlotButton = QtGui.QPushButton('Clear NavPlot')
        self.clearObsPlotButton = QtGui.QPushButton('Clear ObsPlot')
        self.drawTableButton = QtGui.QPushButton('Draw Table')
        self.drawNavPlotButton = QtGui.QPushButton('Draw NavPlot')
        self.drawObsPlotButton = QtGui.QPushButton('Draw MP Plot')
        #Choose functions activating on button click
        self.navFileButton.clicked.connect(self.addNavFile)
        self.obsFileButton.clicked.connect(self.addObsFile)
        self.fileButton.clicked.connect(self.addFile)
        self.clearTableButton.clicked.connect(self.clearTable)
        self.clearNavPlotButton.clicked.connect(self.clearNavPlot)
        self.clearObsPlotButton.clicked.connect(self.clearObsPlot)
        self.drawTableButton.clicked.connect(self.drawTable)
        self.drawNavPlotButton.clicked.connect(self.drawNavPlot)
        self.drawObsPlotButton.clicked.connect(self.drawObsPlot)
        #Set buttons tips (shown while hovering over buttons)
        self.navFileButton.setToolTip('Open navigation Rinex file with extension .??n')
        self.obsFileButton.setToolTip('Open observation Rinex file with extension .??o')
        self.fileButton.setToolTip('Open Rinex file with extension .??n or .??o')
        self.clearTableButton.setToolTip('Clear table and delete Rinex data')
        self.clearNavPlotButton.setToolTip('Clear plot and delete Rinex data')
        self.clearObsPlotButton.setToolTip('Clear plot and delete Rinex data')
        self.drawTableButton.setToolTip('Apply filter to table')
        self.drawNavPlotButton.setToolTip('Draw navplot')
        self.drawObsPlotButton.setToolTip('Draw MP plot')

        #Create combo box widgets
        self.freqChannel = QtGui.QComboBox()
        self.chooseNavParam = QtGui.QComboBox()
        self.chooseNavSat = QtGui.QComboBox()
        self.chooseObsSat = QtGui.QComboBox()
        self.chooseObsFreq1 = QtGui.QComboBox()
        self.chooseObsPseudor1 = QtGui.QComboBox()
        self.chooseObsFreq2 = QtGui.QComboBox()
        self.chooseObsPseudor2 = QtGui.QComboBox()
        self.chooseTableSetting = QtGui.QComboBox()
        self.chooseTableSetting2 = QtGui.QComboBox()
        #Set combo boxes tips (shown while hovering over combo boxes)
        self.freqChannel.setToolTip('Frequency channel for Glonass satellite')
        self.chooseNavParam.setToolTip('Choose parameter you want to plot')
        self.chooseNavSat.setToolTip('Choose satellite you want to plot')
        self.chooseObsSat.setToolTip('Choose satellite you want to plot')
        self.chooseObsFreq1.setToolTip('Choose first frequency')
        self.chooseObsPseudor1.setToolTip('Choose pseudorange observation for the first frequency')
        self.chooseObsFreq2.setToolTip('Choose second frequency')
        self.chooseObsPseudor2.setToolTip('Choose pseudorange observation for the second frequency')
        self.chooseTableSetting.setToolTip('Choose by which element you want to filter')
        self.chooseTableSetting2.setToolTip('Choose by which element you want to filter')
        #Connect to functions
        self.chooseTableSetting.activated[str].connect(self.refreshFilter)
        self.chooseObsSat.activated[str].connect(self.refreshFreq1)
        self.chooseObsSat.activated[str].connect(self.refreshFreqChannel)
        self.chooseObsFreq1.activated[str].connect(self.refreshFreq2)
        self.chooseObsFreq1.activated[str].connect(self.refreshPseudor1)
        self.chooseObsFreq2.activated[str].connect(self.refreshPseudor2)

        #Sets particular widgets as inactive directly after app launch
        self.freqChannel.setEnabled(False)
        self.drawTableButton.setEnabled(False)
        self.drawNavPlotButton.setEnabled(False)
        self.drawObsPlotButton.setEnabled(False)
        self.clearNavPlotButton.setEnabled(False)
        self.clearObsPlotButton.setEnabled(False)
        self.chooseNavParam.setEnabled(False)
        self.chooseNavSat.setEnabled(False)
        self.chooseObsSat.setEnabled(False)
        self.chooseObsFreq1.setEnabled(False)
        self.chooseObsPseudor1.setEnabled(False)
        self.chooseObsFreq2.setEnabled(False)
        self.chooseObsPseudor2.setEnabled(False)
        self.chooseTableSetting.setEnabled(False)
        self.chooseTableSetting2.setEnabled(False)

    def CreateMenus(self):
        """ Function to create menu bar
        """
        self.helpMenu = self.menuBar().addMenu("&Vizrin")

    def CreateActions(self):
        """ Function to create actions
        """
        self.exitAction = QtGui.QAction(QtGui.QIcon('exit.png'), 'E&xit',
                                  self, shortcut="Ctrl+Q",
                                  statusTip="Exit the Application",
                                  triggered=self.exitApp)

        self.aboutAction = QtGui.QAction(QtGui.QIcon('about.png'), 'A&bout',
                                   self, statusTip="Displays information about Vizrin",
                                   triggered=self.aboutApp)

        self.aboutQtAction = QtGui.QAction(QtGui.QIcon('about.png'), '&Platform',
                                         self, statusTip="Displays info about GUI platform",
                                         triggered=self.aboutQt)


    # ---------------------------------------------
    # Functions adding functionality to buttons
    # ---------------------------------------------

    def drawTable(self):
        #self.clearTable()
        if self.chooseTableSetting.currentText() == "Epoch":
            indexlabel = "Satellite  \  Type"
            axis = "items"
            value = str2datetime(self.chooseTableSetting2.currentText())
        elif self.chooseTableSetting.currentText() == "Satellite":
            indexlabel = "Epoch  \  Type"
            axis = "major_axis"
            value = self.chooseTableSetting2.currentText()
            try: value = int(value)
            except:pass
        elif self.chooseTableSetting.currentText() == "Type":
            indexlabel = "Epoch  \  Satellite"
            axis = "minor_axis"
            value = self.chooseTableSetting2.currentText()

        df = Panel2DataFrame(self.rinexFile.GetPanel(),axis,value)
        df[indexlabel] = df.index

        cols = df.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        df = df[cols]

        model = DataFrameModel()
        model.setDataFrame(df)
        self.rinexTable.setModel(model)

    def drawNavPlot(self):
        """ Draws pyqtgraph plot based on parameters set in NavPlotSettings
        """
        #Show elements of the plot
        self.navPlot.setEnabled(True)
        self.navPlot.showAxis("bottom",True)
        self.navPlot.showAxis("left", True)
        self.navPlot.showGrid(True, True, 0.1)
        #Get settings and set labels
        parameter = str(self.chooseNavParam.currentText())
        satellite = int(self.chooseNavSat.currentText())
        #Set labels
        self.navPlot.setLabel("bottom", "hours from the first epoch in file")
        self.navPlot.setLabel("left", parameter)
        #get panel
        panel = self.rinexNavFile.navpanel
        #get a timeseries for a given parameter and satellite
        series = panel.ix[ 0:,satellite,parameter]
        #drop values that lack data
        series = series.dropna()
        #convert pandas series to numpy matrix where column 0 is epochs and column 1 is value of parameter
        matrix = series.reset_index().as_matrix()
        #clear old plot
        self.navPlot.clear()
        #plot data
        self.navPlot.plot(epochs2hours(list(matrix[:,0])), matrix[:,1],pen='g', name=parameter)

    def drawObsPlot(self):
        #Show elements of the plot
        self.obsPlot.setEnabled(True)
        self.obsPlot.showAxis("bottom",True)
        self.obsPlot.showAxis("left", True)
        self.obsPlot.showGrid(True, True, 0.1)
        #Get settings and set labels
        satellite = self.chooseObsSat.currentText()
        f1 = self.chooseObsFreq1.currentText()
        f2 = self.chooseObsFreq2.currentText()
        pr1 = self.chooseObsPseudor1.currentText()
        pr2 = self.chooseObsPseudor2.currentText()
        #Set labels
        self.obsPlot.setLabel("bottom", "hours from the first epoch in file")
        self.obsPlot.setLabel("left", "Multipath")
        #Calculate multipath from rinex data
        multipath = self.rinexObsFile.GetMultipath(satellite,f1,f2,pr1,pr2,self.freqChannel.currentText())
        mp1 = multipath["mp1"]
        mp2 = multipath["mp2"]
        # drop values that lack data
        #mp1 = mp1.dropna()
        #mp2 = mp2.dropna()
        #convert pandas series to numpy matrix where column 0 is epochs and column 1 is value of parameter
        mp1matrix = mp1.reset_index().as_matrix()
        mp2matrix = mp2.reset_index().as_matrix()

        #delete old plot
        self.obsPlot.clear()
        #create new plot
        self.obsPlot.addLegend()

        ar1 = numpy.asarray(epochs2hours(list(mp2matrix[:, 0])),dtype="float64")
        ar2float = numpy.asarray(mp2matrix[:, 1],dtype="float64")
        # plot = pyqtgraph.PlotDataItem(x=ar1, y=ar2float,connect='finite')
        # self.obsPlot.addItem(plot)

        self.obsPlot.plot(x=ar1, y=ar2float,connect='finite',pen='b', name='mp2')

        ar1 = numpy.asarray(epochs2hours(list(mp1matrix[:, 0])), dtype="float64")
        ar2float = numpy.asarray(mp1matrix[:, 1], dtype="float64")
        self.obsPlot.plot(x=ar1, y=ar2float, connect='finite', pen='r', name='mp1')



        #self.obsPlot.plot(epochs2hours(list(mp1matrix[:, 0])), mp1matrix[:, 1],pen='r', name='mp1',connect='finite')



        #self.obsPlot.plot(numpy.asarray(epochs2hours(list(mp2matrix[:, 0]))), mp2matrix[:, 1],pen='b', name='mp2')


    def clearTable(self):
        if hasattr(self, 'rinexFile'):
            del self.rinexFile
        #Empty table
        model = DataFrameModel()
        model.setDataFrame(pandas.DataFrame())
        self.rinexTable.setModel(model)
        #Disable buttons and combo boxes
        self.clearTableButton.setEnabled(False)
        self.drawTableButton.setEnabled(False)
        self.chooseTableSetting.setEnabled(False)
        self.chooseTableSetting2.setEnabled(False)
        #Clears combo boxes
        self.chooseTableSetting.clear()
        self.chooseTableSetting2.clear()
        # Clear file name
        try:
            self.rinexTableName.setText("")
        except: pass

    def clearNavPlot(self):
        #Hide elements of the plot
        self.navPlot.clear()
        self.navPlot.showAxis("bottom",False)
        self.navPlot.showAxis("left", False)
        #Disable plot
        self.navPlot.setEnabled(False)
        #Clear setting combo boxes
        self.chooseNavParam.clear()
        self.chooseNavSat.clear()
        #Disable buttons and combo boxes
        self.drawNavPlotButton.setEnabled(False)
        self.clearNavPlotButton.setEnabled(False)
        self.chooseNavParam.setEnabled(False)
        self.chooseNavSat.setEnabled(False)
        # Clear file name
        self.navPlotName.setText("")

    def clearObsPlot(self):
        #Hide elements of the plot
        self.obsPlot.clear()
        self.obsPlot.showAxis("bottom",False)
        self.obsPlot.showAxis("left", False)
        #Disable plot
        self.obsPlot.setEnabled(False)
        #Clear setting combo boxes
        self.chooseObsSat.clear()
        self.chooseObsFreq1.clear()
        self.chooseObsPseudor1.clear()
        self.chooseObsFreq2.clear()
        self.chooseObsPseudor2.clear()
        self.freqChannel.clear()
        #Disable buttons and combo boxes
        self.drawObsPlotButton.setEnabled(False)
        self.clearObsPlotButton.setEnabled(False)
        self.chooseObsSat.setEnabled(False)
        self.chooseObsFreq1.setEnabled(False)
        self.chooseObsPseudor1.setEnabled(False)
        self.chooseObsFreq2.setEnabled(False)
        self.chooseObsPseudor2.setEnabled(False)
        self.freqChannel.setEnabled(False)
        #Clear file name
        self.obsPlotName.setText("")


    def openRinex(self, fileExt):
        fileName,condition = QtGui.QFileDialog.getOpenFileName(self, str("Open Rinex File"), "", str("Rinex Files " + fileExt))
        self.myStatusBar.showMessage('Loading Rinex File...')

        try:
            if fileName[-1].lower() == 'n' or fileName[-1].lower() == 'g':
                rinexFile = NavFile(fileName)
                self.myStatusBar.showMessage('Rinex navigation file was opened successfully', 10000)
            elif fileName[-1].lower() == 'o':
                rinexFile = ObsFile(fileName)
                self.myStatusBar.showMessage('Rinex observation file was opened successfully', 10000)
            else:
                self.myStatusBar.showMessage("Couldn't load rinex file: Wrong file extension",10000)

            return rinexFile
        except Exception:
            self.myStatusBar.showMessage("Couldn't load rinex file: "+str(sys.exc_info()[1]),10000)


    def addNavFile(self):
        """ Function loading Rinex data for the NavPlotTab
        """
        #self.myStatusBar.showMessage('Loading Rinex File...')
        self.clearNavPlot()
        if hasattr(self, 'rinexNavFile'):
            del self.rinexNavFile
        #Wczytuje plik nawigacyjny
        self.rinexNavFile = self.openRinex("(*.??n *.??g )")
        # Wypisuje nazwę pliku
        self.navPlotName.setText(str(self.rinexNavFile.filename) + "  [" + str(self.rinexNavFile.filepath) + "]")
        #Aktywuje przyciski i rozwijane listy
        self.drawNavPlotButton.setEnabled(True)
        self.clearNavPlotButton.setEnabled(True)
        self.chooseNavParam.setEnabled(True)
        self.chooseNavSat.setEnabled(True)
        #Dodaje elementy do rozwijanych list
        self.chooseNavParam.addItems(self.rinexNavFile.GetParameters())
        self.chooseNavSat.addItems(self.rinexNavFile.GetSatellites())

    def addObsFile(self):
        """ Function loading Rinex data for the ObsPlotTab
        """

        if hasattr(self, 'rinexObsFile'):
            del self.rinexObsFile
        #Wczytuje plik obserwacyjny
        self.rinexObsFile = self.openRinex("(*.??o)")
        #Wypisuje nazwę pliku
        self.obsPlotName.setText(str(self.rinexObsFile.filename) + "  [" + str(self.rinexObsFile.filepath) + "]")
        #Aktywuje przyciski i rozwijane listy
        self.drawObsPlotButton.setEnabled(True)
        self.clearObsPlotButton.setEnabled(True)
        self.chooseObsSat.setEnabled(True)
        self.chooseObsFreq1.setEnabled(True)
        self.chooseObsPseudor1.setEnabled(True)
        self.chooseObsFreq2.setEnabled(True)
        self.chooseObsPseudor2.setEnabled(True)
        #Dodaje elementy do rozwijanych list
        self.chooseObsSat.addItems(self.rinexObsFile.GetSatellites())
        #Refresh combo boxes with frequencies and pseudorange
        self.refreshFreqChannel()
        self.refreshFreq1()
        self.refreshFreq2()
        self.refreshPseudor1()
        self.refreshPseudor2()
        #Update dictionary of frequencies for satellite system of chosen satellite
        #self.updateFreqDict()

    def addFile(self):
        """ Function loading Rinex data for the FileTab
            """
        #Open Rinex file
        if hasattr(self, 'rinexFile'):
            del self.rinexFile
        self.rinexFile = self.openRinex("(*.??o *.??n *.??g )")
        # Wypisuje nazwę pliku
        print str(self.rinexFile.filename)
        self.rinexTableName.setText(str(self.rinexFile.filename) + "  [" + str(self.rinexFile.filepath) + "]")
        #Enable buttons
        self.clearTableButton.setEnabled(True)
        self.drawTableButton.setEnabled(True)
        self.chooseTableSetting.setEnabled(True)
        self.chooseTableSetting2.setEnabled(True)
        #Add lists to comboboxes
        self.chooseTableSetting.clear()
        self.chooseTableSetting.addItems(["Epoch","Satellite","Type"])
        self.refreshFilter()
        #Draw table
        self.drawTable()

    def refreshFilter(self):
        setting = str(self.chooseTableSetting.currentText())
        if setting == "Epoch":
            self.chooseTableSetting2.clear()
            self.chooseTableSetting2.addItems(GetLabelList(self.rinexFile.GetPanel(),"items"))
        elif setting == "Satellite":
            self.chooseTableSetting2.clear()
            self.chooseTableSetting2.addItems(GetLabelList(self.rinexFile.GetPanel(), "major_axis"))
        elif setting == "Type":
            self.chooseTableSetting2.clear()
            self.chooseTableSetting2.addItems(GetLabelList(self.rinexFile.GetPanel(), "minor_axis"))

    def refreshFreq1(self):
        self.chooseObsFreq1.clear()
        df = Panel2DataFrame(self.rinexObsFile.obspanel,"major_axis", str(self.chooseObsSat.currentText()))
        for typ in self.rinexObsFile.GetObsTypes():
            if "L" in typ:
                for element in df[typ]:
                    if str(element) not in ["nan","0.0"]:
                        self.chooseObsFreq1.addItems([typ])
                        break

        if self.chooseObsFreq1.count() < 2:
            self.chooseObsFreq1.setEnabled(False)
        else: self.chooseObsFreq1.setEnabled(True)

        self.refreshPseudor1()
        self.refreshFreq2()

    def refreshFreq2(self):
        self.chooseObsFreq2.clear()
        df = Panel2DataFrame(self.rinexObsFile.obspanel,"major_axis", str(self.chooseObsSat.currentText()))
        for typ in self.rinexObsFile.GetObsTypes():
            if "L" in typ and typ[-1] not in self.chooseObsFreq1.currentText():
                for element in df[typ]:
                    if str(element) not in ["nan","0.0"]:
                        self.chooseObsFreq2.addItems([typ])
                        break

        if self.chooseObsFreq2.count() < 2:
            self.chooseObsFreq2.setEnabled(False)
        else: self.chooseObsFreq2.setEnabled(True)

        self.refreshPseudor2()

    def refreshPseudor1(self):
        self.chooseObsPseudor1.clear()
        df = Panel2DataFrame(self.rinexObsFile.obspanel,"major_axis", str(self.chooseObsSat.currentText()))
        for typ in self.rinexObsFile.GetObsTypes():
            if ("C" in typ or "P" in typ) and typ[-1] in self.chooseObsFreq1.currentText():
                for element in df[typ]:
                    if str(element) not in ["nan","0.0"]:
                        self.chooseObsPseudor1.addItems([typ])
                        break

        if self.chooseObsPseudor1.count() < 2:
            self.chooseObsPseudor1.setEnabled(False)
        else: self.chooseObsPseudor1.setEnabled(True)

    def refreshPseudor2(self):

        self.chooseObsPseudor2.clear()
        df = Panel2DataFrame(self.rinexObsFile.obspanel, "major_axis", str(self.chooseObsSat.currentText()))
        for typ in self.rinexObsFile.GetObsTypes():
            if ("C" in typ or "P" in typ) and typ[-1] in self.chooseObsFreq2.currentText():
                for element in df[typ]:
                    if str(element) not in ["nan", "0.0"]:
                        self.chooseObsPseudor2.addItems([typ])
                        break

        if self.chooseObsPseudor2.count() < 2:
            self.chooseObsPseudor2.setEnabled(False)
        else: self.chooseObsPseudor2.setEnabled(True)

    def refreshFreqChannel(self):
        #TODO UZUPELNIC CHANNLES
        self.freqChannel.clear()
        if "R" in self.chooseObsSat.currentText():
            self.freqChannel.setEnabled(True)
            self.freqChannel.addItems(["-7","-6","-5","-4","-3","-2","-1","0","1","2","3","4","5","6"])
        else:
            self.freqChannel.setEnabled(False)


    def aboutQt(self):
        QtGui.QMessageBox.aboutQt(self,"About Platform")

    def aboutApp(self):
        """ Function creating an about message box
        """
        QtGui.QMessageBox.about(self, "About Vizrin", "Vizrin is a software created by Agnieszka Pogorzelska")

    def exitApp(self):
        self.close()


    # ---------------------------------------------
    # Extra functionality
    # ---------------------------------------------

    def center(self):
        """ Function to center the application
        """
        qRect = self.frameGeometry()
        centerPoint = QtGui.QDesktopWidget().availableGeometry().center()
        qRect.moveCenter(centerPoint)
        self.move(qRect.topLeft())

    def msgApp(self, title, msg):
        """ Function to show Dialog box with provided Title and Message
        """
        userInfo = QMessageBox.question(self, title, msg, QMessageBox.Yes | QMessageBox.No)
        if userInfo == QMessageBox.Yes:
            return "Y"
        if userInfo == QMessageBox.No:
            return "N"

    def CheckRinexVer(self,path):
        #TODO Write function checking rinex version and putting up a messagebox if it's not rinex 2.11
        pass

#---------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        # QApplication.setStyle('plastique')
        myApp = QtGui.QApplication(sys.argv)
        mainWindow = MainWindow()
        myApp.exec_()
        sys.exit(0)
    except NameError:
        print("Name Error:", sys.exc_info()[1])
    except SystemExit:
        print("Closing Window...")
    except Exception:
        print(sys.exc_info()[1])


