class WeightedAverage():
    def __init__(self):
        self.values = []
        self.sum_of_weight = 0
    def add(self, value, weight):
        self.sum_of_weight += weight
        value = 0 if value == None
        weight = 0 if weight == None
        self.values.append((value, weight))
    def average(self):
        if self.sum_of_weight == 0:
            return 0
        return sum(v[0] * v[1] for v in self.values) / self.sum_of_weight