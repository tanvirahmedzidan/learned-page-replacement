import unittest
from main import simulate

class PolicyTests(unittest.TestCase):
    def test_known_reference(self):
        trace = [7,0,1,2,0,3,0,4,2,3,0,3,2]
        for policy, expected in [('FIFO',10),('LRU',9),('Optimal',7)]:
            hits, rows, _, _ = simulate(trace,3,policy)
            self.assertEqual(len(trace)-sum(hits),expected)
            self.assertTrue(all(len(row[4].split()) <= 3 for row in rows))

    def test_repeated_page(self):
        for policy in ['FIFO','LRU','Optimal']:
            self.assertEqual(sum(simulate([1]*10,1,policy)[0]),9)

    def test_optimal_is_lower_bound(self):
        from main import make_trace
        for seed in range(5):
            trace = make_trace(seed,200)
            optimum = sum(simulate(trace,4,'Optimal')[0])
            for policy in ['FIFO','LRU']:
                self.assertGreaterEqual(optimum,sum(simulate(trace,4,policy)[0]))

if __name__ == '__main__':
    unittest.main()
