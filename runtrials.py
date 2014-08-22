from __future__ import division

import collections
import wx

Trial = collections.namedtuple('Trial', 'start goal result time')

class RunTrialsDialog(wx.Dialog):

    def __init__(self, trial_file, maze, block_pos, *args, **kw):
        super(RunTrialsDialog, self).__init__(*args, **kw)

        print trial_file
        
        self.maze = maze
