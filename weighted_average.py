class WeightedAverage():
    def __init__(self):
        self.values = []
        self.sum_of_weight = 0
    def add(self, value, weight):
        self.sum_of_weight += weight
        if value == None:
            value = 0
        if weight == None:
            weight = 0
        self.values.append((value, weight))
    def average(self):
        if len(self.values) == 0:
            return 0
        # if no weight, do normal average
        if self.sum_of_weight == 0:
            return sum(v[0] for v in self.values) / len(self.values)
        return sum(v[0] * v[1] for v in self.values) / self.sum_of_weight