class Timer:
    def __init__(self, count):
        self.count = count
        self.tick = None

    def running(self):
        """Return true if timer is set and running"""
        return bool(self.tick)

    def expired(self, tick):
        """Return true if time has elapsed"""
        return self.running() and tick > self.tick + self.count

    def reset(self, tick):
        """Reset time on timer"""
        self.tick = tick

    def stop(self):
        """Stop timer"""
        self.tick = None
