import datetime

from runtime_verification import event, scope


class Property:
    def __init__(self, scope: scope.Scope, name):
        self.name = name
        self.scope = scope
        self.status = True
        self.is_confirmed = False
        self.confirmedAt = None

    def evaluate(self):
        self.status = True
        return True

    def be_confirmed(self):
        self.is_confirmed = True
        current_time = datetime.datetime.now()
        self.confirmedAt = current_time

    def check(self):
        if not self.is_confirmed:
            if self.scope.check_hold():
                self.evaluate()
            elif self.scope.is_ended and isinstance(self.scope, (scope.BeforeScope, scope.BetweenScope,
                                                                 scope.IntervalScope)):
                self.be_confirmed()


class Absence(Property):
    def __init__(self, event: event.Event, scope):
        super().__init__(scope, "It is never the case that " + event.name + " holds")
        self.event = event

    def evaluate(self):
        self.status = not self.event.check_hold()

        if not self.status:
            self.be_confirmed()


class BoundedExistence(Property):
    def __init__(self, event: event.Event, scope, target_count, is_most):
        if is_most:
            super().__init__(scope, event.name + " holds at most " + target_count + " times")
        else:
            self.status = False
            super().__init__(scope, event.name + " holds at least " + target_count + " times")

        self.event = event
        self.target_count = target_count
        self.current_count = 0
        self.is_most = is_most

    def evaluate(self):
        if self.event.check_hold():
            self.current_count += 1

        if self.is_most and self.current_count > self.target_count:
            self.status = False
            self.be_confirmed()
        elif not self.is_most and self.current_count >= self.target_count:
            self.status = True
            self.be_confirmed()


class Existence(Property):
    def __init__(self, event: event.Event, scope):
        super().__init__(scope, event.name + " holds eventually")
        self.event = event
        self.status = False

    def evaluate(self):
        if self.event.check_hold():
            self.status = True
            self.be_confirmed()


class MinimumDuration(Property):
    def __init__(self, event: event.Event, scope, target):
        super().__init__(scope, event.name + " remains at least " + target)
        self.event = event
        self.target = target
        self.started = None

    def evaluate(self):
        if self.event.check_hold():
            if self.started is None:
                self.started = datetime.datetime.now()
        elif self.started is not None:
            current_duration = datetime.datetime.now() - self.started
            if current_duration < self.target:
                self.status = False
                self.be_confirmed()
            self.started = None


class MaximumDuration(Property):
    def __init__(self, event: event.Event, scope, target):
        super().__init__(scope, event.name + " remains at most " + target)
        self.event = event
        self.target = target
        self.started = None

    def evaluate(self):
        if self.event.check_hold():
            if self.started is None:
                self.started = datetime.datetime.now()
            else:
                current_duration = datetime.datetime.now() - self.started
                if current_duration > self.target:
                    self.status = False
                    self.be_confirmed()

        elif self.started is not None:
            self.started = None


class Precedence(Property):
    def __init__(self, effect: event.Event, cause: event.Event, scope):
        super().__init__(scope,
                         "If " + effect.name + " has occurred, then it must have been " + cause.name + " has occurred before")
        self.effect = effect
        self.cause = cause
        self.cause_occurred = False

    def evaluate(self):
        if self.effect.check_hold():
            if not self.cause_occurred:
                self.status = False
            self.be_confirmed()

        if not self.cause_occurred:
            self.cause_occurred = self.cause.check_hold()


class Prevention(Property):
    def __init__(self, effect: event.Event, cause: event.Event, scope):
        super().__init__(scope,
                         "If " + cause.name + " has occurred, as in response " + effect.name + " never holds")
        self.effect = effect
        self.cause = cause
        self.cause_occurred = False

    def evaluate(self):
        if self.cause_occurred:
            if self.effect.check_hold():
                self.status = False
                self.be_confirmed()

        if not self.cause_occurred:
            self.cause_occurred = self.cause.check_hold()


class Recurrence(Property):
    def __init__(self, event: event.Event, scope, duration):
        super().__init__(scope, event.name + " holds repeatedly at most every " + duration)
        self.event = event
        self.duration = duration
        self.ongoing = False
        self.recent_hold = datetime.datetime.now()

    def evaluate(self):
        if self.event.check_hold():
            if not self.ongoing:
                self.ongoing = True
            self.recent_hold = datetime.datetime.now()
        else:
            self.ongoing = False
            interval = datetime.datetime.now() - self.recent_hold

            if interval > self.duration:
                self.status = False
                self.be_confirmed()


class Response(Property):
    def __init__(self, effect: event.Event, cause: event.Event, scope):
        super().__init__(scope,
                         "If " + cause.name + " has occurred, as in response " + effect.name + " eventually holds")
        self.effect = effect
        self.cause = cause
        self.cause_occurred = False

    def evaluate(self):
        if self.cause_occurred and self.effect.check_hold():
            self.status = True
            self.be_confirmed()

        if not self.cause_occurred and self.cause.check_hold():
            self.status = False
            self.cause_occurred = True


class Universality(Property):
    def __init__(self, event: event.Event, scope):
        super().__init__(scope, "It is always the case that " + event.name + " holds")
        self.event = event

    def evaluate(self):
        if not self.event.check_hold():
            self.status = False
            self.be_confirmed()


class Until(Property):
    def __init__(self, target: event.Event, until: event.Event, scope):
        super().__init__(scope, target.name + " holds without interruption until " + until.name + " holds")
        self.target = target
        self.until = until

    def evaluate(self):
        if self.until.check_hold():
            self.be_confirmed()

        if not self.target.check_hold():
            self.status = False
            self.be_confirmed()
