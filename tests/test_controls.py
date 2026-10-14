import unittest
from desktop_cast.store import control_values, CONTROL_DEFAULTS
class ControlsTests(unittest.TestCase):
    def test_clamps_speed_size_rotation_and_volume(self):
        self.assertEqual(control_values({'fps':1000,'size':1,'rotation':-900,'volume':2}),
                         {'fps':120,'size':64,'rotation':-180,'volume':1})
    def test_boolean_and_layer_validation(self):
        with self.assertRaises(ValueError):control_values({'locked':'false'})
        with self.assertRaises(ValueError):control_values({'layer':'arbitrary'})
        self.assertEqual(control_values({'clickthrough':True,'locked':False}),{'clickthrough':True,'locked':False})
    def test_reset_is_recoverable(self):
        self.assertFalse(CONTROL_DEFAULTS['clickthrough'])
        self.assertFalse(CONTROL_DEFAULTS['hide_cursor'])
        self.assertFalse(CONTROL_DEFAULTS['locked'])
        self.assertEqual(CONTROL_DEFAULTS['rotation'],0)
        self.assertEqual(CONTROL_DEFAULTS['fps'],15)
if __name__=='__main__':unittest.main()
