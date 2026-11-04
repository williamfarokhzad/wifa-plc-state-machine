import itertools
import unittest
from main import Conveyor, Inputs, run_scenario

class MachineTests(unittest.TestCase):
    def test_normal_trace(self):
        m = Conveyor()
        rows = [m.step(i) for i in [Inputs(), Inputs(start=True), Inputs(), Inputs(part=True), Inputs(reset=True)]]
        self.assertEqual([r["state"] for r in rows], ["IDLE","RUNNING","RUNNING","COMPLETE","IDLE"])
        self.assertEqual([r["motor"] for r in rows], [False,True,True,False,False])

    def test_deadline_and_sensor_priority(self):
        for detected, expected in [(False,"FAULT"),(True,"COMPLETE")]:
            m=Conveyor(3);m.step(Inputs(start=True))
            self.assertEqual(m.step(Inputs())["age_scans"],1)
            self.assertEqual(m.step(Inputs())["state"],"RUNNING")
            self.assertEqual(m.step(Inputs(part=detected))["state"],expected)

    def test_stop_wins_over_part(self):
        m=Conveyor();m.step(Inputs(start=True))
        self.assertEqual(m.step(Inputs(stop=True,part=True))["state"],"IDLE")

    def test_permit_wins_over_stop_and_reset(self):
        m=Conveyor();m.step(Inputs(start=True))
        r=m.step(Inputs(permit=False,stop=True,reset=True))
        self.assertEqual((r["state"],r["motor"]),("FAULT",False))

    def test_held_start_does_not_restart_after_stop(self):
        m=Conveyor();m.step(Inputs(start=True));m.step(Inputs(start=True,stop=True))
        self.assertEqual(m.step(Inputs(start=True))["state"],"IDLE")
        m.step(Inputs());self.assertTrue(m.step(Inputs(start=True))["motor"])

    def test_reset_requires_new_edge_after_permit_returns(self):
        m=Conveyor();m.step(Inputs(permit=False,reset=True))
        self.assertEqual(m.step(Inputs(reset=True))["state"],"FAULT")
        m.step(Inputs());self.assertEqual(m.step(Inputs(reset=True))["state"],"IDLE")

    def test_one_transition_per_scan(self):
        m=Conveyor();m.step(Inputs(permit=False))
        self.assertEqual(m.step(Inputs(reset=True,start=True))["state"],"IDLE")
        self.assertEqual(m.step(Inputs(start=True))["state"],"IDLE")

    def test_part_blocks_start(self):
        self.assertEqual(Conveyor().step(Inputs(start=True,part=True))["state"],"IDLE")

    def test_complete_latches(self):
        m=Conveyor();m.step(Inputs(start=True));m.step(Inputs(part=True))
        for _ in range(10):self.assertEqual(m.step(Inputs())["state"],"COMPLETE")

    def test_all_two_scan_boolean_combinations(self):
        frames=[Inputs(*v) for v in itertools.product([False,True],repeat=5)]
        for a,b in itertools.product(frames,repeat=2):
            m=Conveyor(1)
            for frame in [a,b]:
                row=m.step(frame)
                self.assertEqual(row["motor"],row["state"]=="RUNNING")
                if frame.stop or not frame.permit:self.assertFalse(row["motor"])

    def test_time_and_missing_input_semantics(self):
        rows=run_scenario({"timeout_scans":1,"scan_ms":100,"scans":[{"start":True},{}]})
        self.assertEqual([r["time_ms"] for r in rows],[0,100])
        self.assertFalse(rows[1]["start"])
        self.assertEqual(rows[1]["reason"],"timeout")

    def test_bad_inputs_and_configs(self):
        for value in [0,-1,True,1.5,100001]:
            with self.assertRaises(ValueError):Conveyor(value)
        for value in [1,"false",None]:
            with self.assertRaises(ValueError):Inputs(start=value)
        base={"timeout_scans":5,"scan_ms":100,"scans":[{}]}
        for patch in [{"scan_ms":False},{"scans":[]},{"scans":[{"strat":True}]},{"scans":[{"part":1}]}]:
            with self.assertRaises(ValueError):run_scenario({**base,**patch})

if __name__=="__main__":unittest.main()
