"""Widgets containing notes (such as bookmarks, events, and stages).

  - bookmarks are unique (might have the same text) and are not mutually
    exclusive
  - events are not unique and are not mutually exclusive
  - states are not unique and are mutually exclusive

"""
from logging import getLogger
lg = getLogger(__name__)

from datetime import datetime, timedelta
from functools import partial
from getpass import getuser
from math import floor
from os.path import basename, exists, splitext
from xml.etree.ElementTree import Element, SubElement

from PyQt4.QtGui import (QAbstractItemView,
                         QAction,
                         QComboBox,
                         QFormLayout,
                         QPushButton,
                         QLabel,
                         QTableView,
                         QTableWidget,
                         QTableWidgetItem,
                         QWidget,
                         )

from ..attr import Scores

STAGE_NAME = ['Wake', 'Movement', 'REM', 'NREM1', 'NREM2', 'NREM3', 'Unknown']
STAGE_SHORTCUT = ['9', '8', '5', '1', '2', '3', '0']
DATA_FOLDER = '/eeg/raw/xltek/'
SCORES_FOLDER = '/doc/scores/'


class Bookmarks(QTableWidget):
    """Keep track of all the bookmarks.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    bookmarks : list of dict
        each dict contains time (in s from beginning of file) and name

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.bookmarks = []

        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Time', 'Text'])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cellDoubleClicked.connect(self.move_to_bookmark)

    def update_bookmarks(self, header):
        """Update the bookmarks info

        Parameters
        ----------
        header : dict
            header of the dataset

        """
        bookmarks = []
        splitted = header['orig']['notes'].split('\n')
        for bm in splitted:
            values = bm.split(',')
            bm_time = datetime.strptime(values[0], '%Y-%m-%dT%H:%M:%S')
            bm_sec = (bm_time - header['start_time']).total_seconds()

            bookmarks.append({'time': bm_sec,
                              'name': ','.join(values[2:])
                              })

        self.bookmarks = bookmarks
        self.display_bookmarks()

    def display_bookmarks(self):
        """Update the table with bookmarks."""
        start_time = self.parent.info.dataset.header['start_time']

        self.setRowCount(len(self.bookmarks))
        for i, bm in enumerate(self.bookmarks):
            abs_time = (start_time +
                        timedelta(seconds=bm['time'])).strftime('%H:%M:%S')
            self.setItem(i, 0, QTableWidgetItem(abs_time))
            self.setItem(i, 1, QTableWidgetItem(bm['name']))

        self.parent.overview.mark_bookmarks()

    def move_to_bookmark(self, row, col):
        """Move to point in time marked by the bookmark.

        Parameters
        ----------
        row : QtCore.int

        column : QtCore.int

        """
        window_length = self.parent.overview.window_length
        bookmark_time = self.bookmarks[row]['time']
        window_start = floor(bookmark_time / window_length) * window_length
        self.parent.overview.update_position(window_start)


class Events(QWidget):
    """

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.idx_stages = QComboBox()
        self.table = QTableView()

        layout = QFormLayout()
        layout.addRow('Events: ', self.idx_stages)
        layout.addRow('List: ', self.table)
        self.setLayout(layout)

    def update_events(self):
        """

        """

        self.display_events()

    def display_events(self):
        pass


class Stages(QWidget):
    """Widget that contains information about sleep scoring.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    scores : instance of Scores
        information about sleep staging
    idx_filename : instance of QPushButton
        push button to open a new file
    idx_rater : instance of QLabel
        widget wit the name of the rater
    idx_stages : instance of QComboBox
        widget with the possible sleep stages
    action : dict
        names of all the actions related to sleep scoring

    """
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.action = {}
        self.scores = None
        self.idx_filename = QPushButton('Click to open sleep scores')
        self.idx_filename.clicked.connect(self.action_open_predefined_stages)
        self.idx_rater = QLabel()
        self.idx_stages = QComboBox()
        self.idx_stages.activated.connect(self.get_sleepstage)

        layout = QFormLayout()
        layout.addRow('Filename: ', self.idx_filename)
        layout.addRow('Rater: ', self.idx_rater)
        layout.addRow('Stage: ', self.idx_stages)
        self.setLayout(layout)

    def action_open_predefined_stages(self):
        """Try to open the score file automatically.

        It inferes the name of the score file based on the name of the
        dataset. I don't like this solution, because it's very specific to
        the organization of the folders on my computer, but it saves me quite
        some time.

        """
        filename = splitext(self.parent.info.filename)[0] + '_scores.xml'
        filename = filename.replace(DATA_FOLDER, SCORES_FOLDER)
        if exists(filename):
            self.update_stages(filename)
        else:
            self.parent.action_open_stages()

    def update_stages(self, xml_file):
        """Update information about the sleep scoring.

        Parameters
        ----------
        xml_file : str
            file of the new or existing .xml file

        """
        try:
            self.scores = Scores(xml_file)
        except FileNotFoundError:
            root = self.create_empty_xml()
            self.scores = Scores(xml_file, root)
        self.display_stages()
        self.create_actions()

    def display_stages(self):
        """Update the widgets of the sleep scoring."""
        self.idx_filename.setText(basename(self.scores.xml_file))
        self.idx_rater.setText(self.scores.get_rater())
        for one_stage in STAGE_NAME:
            self.idx_stages.addItem(one_stage)

        for epoch in self.scores.get_epochs():
            self.parent.overview.mark_stages(epoch['start_time'],
                                             epoch['end_time'] -
                                             epoch['start_time'],
                                             epoch['stage'])

    def create_actions(self):
        """Create actions and shortcut to score sleep."""
        actions = {}
        for one_stage, one_shortcut in zip(STAGE_NAME, STAGE_SHORTCUT):
            actions[one_stage] = QAction('Score as ' + one_stage, self.parent)
            actions[one_stage].setShortcut(one_shortcut)
            stage_idx = STAGE_NAME.index(one_stage)
            actions[one_stage].triggered.connect(partial(self.get_sleepstage,
                                                         stage_idx))
            self.addAction(actions[one_stage])
        self.action = actions

    def get_sleepstage(self, stage_idx=None):
        """Get the sleep stage, using shortcuts or combobox.

        Parameters
        ----------
        stage : str
            string with the name of the sleep stage.

        """
        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length

        id_window = str(window_start)
        lg.info('User staged ' + id_window + ' as ' + STAGE_NAME[stage_idx])
        self.scores.set_stage_for_epoch(id_window, STAGE_NAME[stage_idx])
        self.set_combobox_index()
        self.parent.overview.mark_stages(window_start, window_length,
                                         STAGE_NAME[stage_idx])
        self.parent.action_page_next()

    def set_combobox_index(self):
        """Set the current stage in combobox."""
        window_start = self.parent.overview.window_start
        stage = self.scores.get_stage_for_epoch(str(window_start))
        lg.debug('Set combobox at ' + stage)
        self.idx_stages.setCurrentIndex(STAGE_NAME.index(stage))

    def create_empty_xml(self):
        """Create a new empty xml file, to keep the sleep scoring.

        It's organized with sleep_stages (and filename of the dataset), rater
        (with the name of the rater), epochs (with id equal to the start_time),
        which have start_time, end_time, and stage.

        """
        minimum = int(floor(self.parent.overview.minimum))
        maximum = int(floor(self.parent.overview.maximum))
        window_length = self.parent.preferences.values['stages/scoring_window']

        main = Element('sleep_stages')
        main.set('filename', self.parent.info.filename)
        rated = SubElement(main, 'rater')
        rated.set('name', getuser())

        for t in range(minimum, maximum, window_length):
            epoch = SubElement(rated, 'epoch')
            epoch.set('id', str(t))  # use start_time as id

            start_time = SubElement(epoch, 'start_time')
            start_time.text = str(t)

            end_time = SubElement(epoch, 'end_time')
            end_time.text = str(t + window_length)

            stage = SubElement(epoch, 'stage')
            stage.text = 'Unknown'

        return main
