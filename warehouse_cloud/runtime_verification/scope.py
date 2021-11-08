import datetime


class Scope:
    def __init__(self, name):
        self.name = name
        self.is_started = False
        self.is_ended = False

    def check_hold(self):
        return False


class AfterScope(Scope):
    def __init__(self, event):
        super().__init__("After " + event.name)
        self.end_event = event

    def check_hold(self):
        if self.is_started:
            return True

        if self.end_event.check_hold():
            self.is_started = True
            return True

        return False


class BeforeScope(Scope):
    def __init__(self, event):
        super().__init__("Before " + event.name)
        self.start_event = event
        self.is_started = True

    def check_hold(self):
        if self.is_ended:
            return False

        if self.start_event.check_hold():
            self.is_ended = True
            return False

        return True


class BetweenScope(Scope):
    def __init__(self, start_event, end_event):
        super().__init__("Between " + start_event.name + " and " + end_event.name)
        self.start_event = start_event
        self.end_event = end_event

    def check_hold(self):
        if not self.is_started:
            if self.start_event.check_hold():
                self.is_started = True
                return True
            return False

        if not self.is_ended:
            if self.end_event.check_hold():
                self.is_ended = True
                return False

        return True


class DuringScope(Scope):
    def __init__(self, event):
        super().__init__("During " + event.name)
        self.event = event

    def check_hold(self):
        return self.event.check_hold()


class GloballyScope(Scope):
    def __init__(self, event):
        super().__init__("Globally")
        self.is_started = True

    def check_hold(self):
        return True


class IntervalScope(Scope):
    def __init__(self, start, end):
        super().__init__("Interval from " + start + " to " + end)
        self.start = start
        self.end = end

    def check_hold(self):
        return self.start <= datetime.datetime.now() <= self.end
