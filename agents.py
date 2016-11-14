"""Implement Agents and Environments (Chapters 1-2).

Thing ## A physical object that can exist in an environment
    Agent
        Wumpus
    Dirt
    Wall
    ...

Environment ## An environment holds objects, runs simulations
    XYEnvironment
        VacuumEnvironment
        WumpusEnvironment

An agent program is a callable instance, taking percepts and choosing actions
    SimpleReflexAgentProgram
    ...

EnvGUI ## A window with a graphical representation of the Environment

EnvToolbar ## contains buttons for controlling EnvGUI

EnvCanvas ## Canvas to display the environment of an EnvGUI

"""

from utils import *
import random, copy


class Thing(object):
   
    def __repr__(self):
        return '<%s>' % getattr(self, '__name__', self.__class__.__name__)

    def is_alive(self):
        return hasattr(self, 'alive') and self.alive

    def show_state(self):
        print "I don't know how to show_state."

    def display(self, canvas, x, y, width, height):
        pass

class Agent(Thing):
    def __init__(self, program=None):
        self.alive = True
        self.bump = False
        if program is None:
            def program(percept):
                return raw_input('Percept=%s; action? ' % percept)
        assert callable(program)
        self.program = program

    def can_grab(self, thing):
        return False

def TraceAgent(agent):
    old_program = agent.program
    def new_program(percept):
        action = old_program(percept)
        print '%s perceives %s and does %s' % (agent, percept, action)
        return action
    agent.program = new_program
    return agent

def TableDrivenAgentProgram(table):
    percepts = []
    def program(percept):
        percepts.append(percept)
        action = table.get(tuple(percepts))
        return action
    return program

def RandomAgentProgram(actions):
    return lambda percept: random.choice(actions)

def SimpleReflexAgentProgram(rules, interpret_input):
    def program(percept):
        state = interpret_input(percept)
        rule = rule_match(state, rules)
        action = rule.action
        return action
    return program

def ModelBasedReflexAgentProgram(rules, update_state):
    def program(percept):
        program.state = update_state(program.state, program.action, percept)
        rule = rule_match(program.state, rules)
        action = rule.action
        return action
    program.state = program.action = None
    return program

def rule_match(state, rules):
    for rule in rules:
        if rule.matches(state):
            return rule

loc_A, loc_B = (0, 0), (1, 0) # The two locations for the Vacuum world


def RandomVacuumAgent():
    return Agent(RandomAgentProgram(['Right', 'Left', 'Suck', 'NoOp']))


def TableDrivenVacuumAgent():
    table = {((loc_A, 'Clean'),): 'Right',
             ((loc_A, 'Dirty'),): 'Suck',
             ((loc_B, 'Clean'),): 'Left',
             ((loc_B, 'Dirty'),): 'Suck',
             ((loc_A, 'Clean'), (loc_A, 'Clean')): 'Right',
             ((loc_A, 'Clean'), (loc_A, 'Dirty')): 'Suck',
             # ...
             ((loc_A, 'Clean'), (loc_A, 'Clean'), (loc_A, 'Clean')): 'Right',
             ((loc_A, 'Clean'), (loc_A, 'Clean'), (loc_A, 'Dirty')): 'Suck',
             # ...
             }
    return Agent(TableDrivenAgentProgram(table))


def ReflexVacuumAgent():
    def program((location, status)):
        if status == 'Dirty': return 'Suck'
        elif location == loc_A: return 'Right'
        elif location == loc_B: return 'Left'
    return Agent(program)

def ModelBasedVacuumAgent():
    model = {loc_A: None, loc_B: None}
    def program((location, status)):
        model[location] = status ## Update the model here
        if model[loc_A] == model[loc_B] == 'Clean': return 'NoOp'
        elif status == 'Dirty': return 'Suck'
        elif location == loc_A: return 'Right'
        elif location == loc_B: return 'Left'
    return Agent(program)

#______________________________________________________________________________


class Environment(object):
    def __init__(self):
        self.things = []
        self.agents = []

    def thing_classes(self):
        return [] ## List of classes that can go into environment

    def percept(self, agent):
        abstract

    def execute_action(self, agent, action):
        abstract

    def default_location(self, thing):
        return None

    def exogenous_change(self):
        pass

    def is_done(self):
        return not any(agent.is_alive() for agent in self.agents)

    def step(self):
        if not self.is_done():
            actions = [agent.program(self.percept(agent))
                       for agent in self.agents]
            for (agent, action) in zip(self.agents, actions):
                self.execute_action(agent, action)
            self.exogenous_change()

    def run(self, steps=1000):
        for step in range(steps):
            if self.is_done(): return
            self.step()

    def list_things_at(self, location, tclass=Thing):
        return [thing for thing in self.things
                if thing.location == location and isinstance(thing, tclass)]

    def some_things_at(self, location, tclass=Thing):
        return self.list_things_at(location, tclass) != []

    def add_thing(self, thing, location=None):
        if not isinstance(thing, Thing):
            thing = Agent(thing)
        assert thing not in self.things, "Don't add the same thing twice"
        thing.location = location or self.default_location(thing)
        self.things.append(thing)
        if isinstance(thing, Agent):
            thing.performance = 0
            self.agents.append(thing)

    def delete_thing(self, thing):
        try:
            self.things.remove(thing)
        except ValueError, e:
            print e
            print "  in Environment delete_thing"
            print "  Thing to be removed: %s at %s" % (thing, thing.location)
            print "  from list: %s" % [(thing, thing.location)
                                       for thing in self.things]
        if thing in self.agents:
            self.agents.remove(thing)

class XYEnvironment(Environment):
    def __init__(self, width=10, height=10):
        super(XYEnvironment, self).__init__()
        update(self, width=width, height=height, observers=[])

    def things_near(self, location, radius=None):
        if radius is None: radius = self.perceptible_distance
        radius2 = radius * radius
        return [thing for thing in self.things
                if distance2(location, thing.location) <= radius2]

    perceptible_distance = 1

    def percept(self, agent):
        return [self.thing_percept(thing, agent)
                for thing in self.things_near(agent.location)]

    def execute_action(self, agent, action):
        agent.bump = False
        if action == 'TurnRight':
            agent.heading = self.turn_heading(agent.heading, -1)
        elif action == 'TurnLeft':
            agent.heading = self.turn_heading(agent.heading, +1)
        elif action == 'Forward':
            self.move_to(agent, vector_add(agent.heading, agent.location))
#         elif action == 'Grab':
#             things = [thing for thing in self.list_things_at(agent.location)
#                     if agent.can_grab(thing)]
#             if things:
#                 agent.holding.append(things[0])
        elif action == 'Release':
            if agent.holding:
                agent.holding.pop()

    def thing_percept(self, thing, agent): 
        "Return the percept for this thing."
        return thing.__class__.__name__

    def default_location(self, thing):
        return (random.choice(self.width), random.choice(self.height))

    def move_to(self, thing, destination):
        "Move a thing to a new location."
        thing.bump = self.some_things_at(destination, Obstacle)
        if not thing.bump:
            thing.location = destination
            for o in self.observers:
                o.thing_moved(thing)

    def add_thing(self, thing, location=(1, 1)):
        super(XYEnvironment, self).add_thing(thing, location)
        thing.holding = []
        thing.held = None
        for obs in self.observers:
            obs.thing_added(thing)

    def delete_thing(self, thing):
        super(XYEnvironment, self).delete_thing(thing)
        for obs in self.observers:
            obs.thing_deleted(thing)

    def add_walls(self):
        for x in range(self.width):
            self.add_thing(Wall(), (x, 0))
            self.add_thing(Wall(), (x, self.height-1))
        for y in range(self.height):
            self.add_thing(Wall(), (0, y))
            self.add_thing(Wall(), (self.width-1, y))

    def add_observer(self, observer):
        self.observers.append(observer)

    def turn_heading(self, heading, inc):
        return turn_heading(heading, inc)

class Obstacle(Thing):
    pass

class Wall(Obstacle):
    pass

class Dirt(Thing):
    pass

class VacuumEnvironment(XYEnvironment):
    def __init__(self, width=10, height=10):
        super(VacuumEnvironment, self).__init__(width, height)
        self.add_walls()

    def thing_classes(self):
        return [Wall, Dirt, ReflexVacuumAgent, RandomVacuumAgent,
                TableDrivenVacuumAgent, ModelBasedVacuumAgent]

    def percept(self, agent):
        status = if_(self.some_things_at(agent.location, Dirt),
                     'Dirty', 'Clean')
        bump = if_(agent.bump, 'Bump', 'None')
        return (status, bump)

    def execute_action(self, agent, action):
        if action == 'Suck':
            dirt_list = self.list_things_at(agent.location, Dirt)
            if dirt_list != []:
                dirt = dirt_list[0]
                agent.performance += 100
                self.delete_thing(dirt)
        else:
            super(VacuumEnvironment, self).execute_action(agent, action)

        if action != 'NoOp':
            agent.performance -= 1

class TrivialVacuumEnvironment(Environment):
    def __init__(self):
        super(TrivialVacuumEnvironment, self).__init__()
        self.status = {loc_A: random.choice(['Clean', 'Dirty']),
                       loc_B: random.choice(['Clean', 'Dirty'])}

    def thing_classes(self):
        return [Wall, Dirt, ReflexVacuumAgent, RandomVacuumAgent,
                TableDrivenVacuumAgent, ModelBasedVacuumAgent]

    def percept(self, agent):
        "Returns the agent's location, and the location status (Dirty/Clean)."
        return (agent.location, self.status[agent.location])

    def execute_action(self, agent, action):
        if action == 'Right':
            agent.location = loc_B
            agent.performance -= 1
        elif action == 'Left':
            agent.location = loc_A
            agent.performance -= 1
        elif action == 'Suck':
            if self.status[agent.location] == 'Dirty':
                agent.performance += 10
            self.status[agent.location] = 'Clean'

    def default_location(self, thing):
        "Agents start in either location at random."
        return random.choice([loc_A, loc_B])

class Gold(Thing): pass
class Pit(Thing): pass
class Arrow(Thing): pass
class Wumpus(Agent): pass
class Explorer(Agent): pass

class WumpusEnvironment(XYEnvironment):

    def __init__(self, width=10, height=10):
        super(WumpusEnvironment, self).__init__(width, height)
        self.add_walls()

    def thing_classes(self):
        return [Wall, Gold, Pit, Arrow, Wumpus, Explorer]

def compare_agents(EnvFactory, AgentFactories, n=10, steps=1000):
    envs = [EnvFactory() for i in range(n)]
    return [(A, test_agent(A, steps, copy.deepcopy(envs)))
            for A in AgentFactories]

def test_agent(AgentFactory, steps, envs):
    def score(env):
        agent = AgentFactory()
        env.add_thing(agent)
        env.run(steps)
        return agent.performance
    return mean(map(score, envs))

__doc__ += """
>>> a = ReflexVacuumAgent()
>>> a.program((loc_A, 'Clean'))
'Right'
>>> a.program((loc_B, 'Clean'))
'Left'
>>> a.program((loc_A, 'Dirty'))
'Suck'
>>> a.program((loc_A, 'Dirty'))
'Suck'

>>> e = TrivialVacuumEnvironment()
>>> e.add_thing(ModelBasedVacuumAgent())
>>> e.run(5)

## Environments, and some agents, are randomized, so the best we can
## give is a range of expected scores.  If this test fails, it does
## not necessarily mean something is wrong.
>>> envs = [TrivialVacuumEnvironment() for i in range(100)]
>>> def testv(A): return test_agent(A, 4, copy.deepcopy(envs))
>>> 7 < testv(ModelBasedVacuumAgent) < 11
True
>>> 5 < testv(ReflexVacuumAgent) < 9
True
>>> 2 < testv(TableDrivenVacuumAgent) < 6
True
>>> 0.5 < testv(RandomVacuumAgent) < 3
True
"""

import Tkinter as tk

class EnvGUI(tk.Tk, object):

    def __init__(self, env, title = 'AIMA GUI', cellwidth=50, n=10):

        super(EnvGUI, self).__init__()
        self.title(title)
        canvas = EnvCanvas(self, env, cellwidth, n)
        toolbar = EnvToolbar(self, env, canvas)
        for w in [canvas, toolbar]:
            w.pack(side="bottom", fill="x", padx="3", pady="3")


class EnvToolbar(tk.Frame, object):

    def __init__(self, parent, env, canvas):
        super(EnvToolbar, self).__init__(parent, relief='raised', bd=2)

        self.env = env
        self.canvas = canvas
        self.running = False
        self.speed = 1.0

        for txt, cmd in [('Step >', self.env.step),
                         ('Run >>', self.run),
                         ('Stop [ ]', self.stop),
                         ('List things', self.list_things),
                         ('List agents', self.list_agents)]:
            tk.Button(self, text=txt, command=cmd).pack(side='left')

        tk.Label(self, text='Speed').pack(side='left')
        scale = tk.Scale(self, orient='h',
                         from_=(1.0), to=10.0, resolution=1.0,
                         command=self.set_speed)
        scale.set(self.speed)
        scale.pack(side='left')

    def run(self):
        print 'run'
        self.running = True
        self.background_run()

    def stop(self):
        print 'stop'
        self.running = False

    def background_run(self):
        if self.running:
            self.env.step()
            # ms = int(1000 * max(float(self.speed), 0.5))
            #ms = max(int(1000 * float(self.delay)), 1)
            delay_sec = 1.0 / max(self.speed, 1.0) 
            ms = int(1000.0 * delay_sec)  
            self.after(ms, self.background_run)

    def list_things(self):
        print "Things in the environment:"
        for thing in self.env.things:
            print "%s at %s" % (thing, thing.location)

    def list_agents(self):
        print "Agents in the environment:"
        for agt in self.env.agents:
            print "%s at %s" % (agt, agt.location)

    def set_speed(self, speed):
        self.speed = float(speed)

