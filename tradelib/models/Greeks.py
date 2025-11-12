class Greeks:
    def __init__(self, delta=0, theta=0, gamma=0, vega=0, sigma=0) -> None:
        self.delta = delta
        self.theta = theta
        self.gamma = gamma
        self.vega = vega
        self.sigma =sigma