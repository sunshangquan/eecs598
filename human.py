from abc import ABC, ABCMeta, abstractmethod
from model_util import Event, MoveBodyPartEvent
from operators import OperatorElement, Perceptual, Encode, Cognitive, RetrieveTargetLocation, ActivateTargetLocation, \
    MotorOperator, Move
import networkx as nx
import math
import numpy as np
from string import ascii_lowercase
from collections import OrderedDict
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from device import Device, TouchScreenKeyboardDeviceDirector

key2device = {
    'presentMode': 'keyboard_2',
    '<': 'keyboard_4',
    'bright_2': 'keyboard_3',
    'esc': 'keyboard_2',
    'out_4': 'keyboard_2',
    'out_3': 'keyboard_2',
}

touch_bar_keys = [ 'esc','paste','newSlide','table','picture','shapes','TextBox','copy','presentMode',"<",'bright_1','volumn_1','mute_1','siri_1',
                   'End Show', 'slides', 'time', 'rehearse', "<",'bright_2','volumn_2','mute_2','siri_2',
                   'bright-', 'slider', 'bright+', 'out_3',
                   'out_4', 'light-', 'light+', 'layout', 'launchpad', 'keylight-', 'keylight+', '<<', '>||', '>>', 'mute_4', 'vol-', 'vol+', 'siri_4']

keyboard_1 = ['esc','paste','newSlide','table','picture','shapes','TextBox','copy','presentMode',"<",'bright_1','volumn_1','mute_1','siri_1']
keyboard_2 = ['End Show', 'slides', 'time', 'rehearse', "<",'bright_2','volumn_2','mute_2','siri_2']
keyboard_3 = ['bright-', 'slider', 'bright+', 'out_3']
keyboard_4 = ['out_4', 'light-', 'light+', 'layout', 'launchpad', 'keylight-', 'keylight+', '<<', '>||', '>>', 'mute_4', 'vol-', 'vol+', 'siri_4']

class Human():
    '''
    This class represents a human with both cognition and body. In Assignment 2, this will be an abstraction where
    most complex aspects of the human will be removed, except body parts.
    '''

    def __init__(self, handler=None):
        self.body_parts = {}
        self.handler = handler

        # Controls how far random visual search jumps from current fixation.
        self.visual_search_sigma = 100

        self.timestamp_offset = 0

    def add_body_part(self, body_part):
        self.body_parts[body_part.name] = body_part

    def create_finger(self, name, location_x, location_y):
        '''  Creates and adds a new figure to  the human. '''
        finger = Finger(name, location_x, location_y, self.handler)
        self.add_body_part(finger)
        return finger

    def create_eyes(self, name, location_x, location_y, handler_distance):
        '''  Creates and adds a new figure to  the human. '''
        eyes = Eyes(name, location_x, location_y, handler_distance, self.handler)
        self.add_body_part(eyes)
        return eyes

    def create_ltm(self, name, store={}, activations={}):
        '''  Creates and adds a new figure to  the human. '''
        ltm = LongTermMemory(name, store, activations)
        self.add_body_part(ltm)

        return ltm

    def create_stm(self, name):
        '''  Creates and adds a new figure to  the human. '''
        stm = ShortTermMemory(name, storage_capacity=20)
        self.add_body_part(stm)

        return stm

    def press(self, input):
        current_keyboard = "keyboard_1"
        ''' Instructs the human to press on a series of targets. The human implementation simulates and predict behavior and returns a resulting schedule chart. Clients can then evaluate the schedule chart for duration of operations.'''
        schedule_chart = nx.DiGraph()

        operator_idx = 0
        previous_perceptual_operator = None
        previous_perceptual_word_operator = None
        previous_cognitive_operator = None
        previous_cognitive_retrieve_operator = None
        previous_cognitive_nonactivation_operator = None
        previous_motor_finger_operator = None
        previous_motor_eyes_operator = None

        word = input.split(',')

        # NOT NEEDED
        # Chunk up words in 3-grams.
        # phrase = ''
        # word_index = 0
        # for word in words:
        #     word_index += 1
        #
        #     phrase = phrase + word
        #
        #     if word_index < len(words):
        #         if word_index % 10 == 0:
        #             phrase = phrase + '|'
        #         else:
        #             phrase = phrase + '\t'
        #
        # words = phrase.split("|")

        print(word)
        # Move eyes to the phrase.
        escape_key = self.handler.find_descendant('esc')
        move_eyes = Move(str(operator_idx) + '_motor_eyes:' + escape_key.name, self.body_parts['eyes'],
                         escape_key)
        schedule_chart.add_node(move_eyes)
        operator_idx += 1

        move_eyes.execute()

        if previous_cognitive_operator is not None:
            schedule_chart.add_edge(previous_cognitive_operator, move_eyes)

        if previous_perceptual_operator is not None:
            schedule_chart.add_edge(previous_perceptual_operator, move_eyes)

        if previous_motor_eyes_operator is not None:
            schedule_chart.add_edge(previous_motor_eyes_operator, move_eyes)

        previous_motor_eyes_operator = move_eyes

        # Find which target we intersect with.
        intersecting_event = Event(self.body_parts['eyes'].fixation_x, self.body_parts['eyes'].fixation_y)
        intersecting_handler = self.handler.find_intersect(intersecting_event, current_keyboard)

        if intersecting_handler is not None:

            encode_operator = None

            while encode_operator is None or encode_operator.initiate_saccade:
                # This should always be true; otherwise, we have gone out of the environment.
                encode_operator = Encode(str(operator_idx) + '_encode:' + intersecting_handler.name,
                                         self.body_parts['eyes'], intersecting_handler)
                schedule_chart.add_node(encode_operator)
                operator_idx += 1

                encode_operator.execute()

                if previous_perceptual_operator is not None:
                    schedule_chart.add_edge(previous_perceptual_operator, encode_operator)

                if previous_motor_eyes_operator is not None:
                    schedule_chart.add_edge(previous_motor_eyes_operator, encode_operator)

                previous_perceptual_operator = encode_operator

                if encode_operator.initiate_saccade:
                    # We did not encode the handler under the fixation point in time and we need another saccade.
                    move_eyes = Move(str(operator_idx) + '_motor_eyes:' + intersecting_handler.name,
                                     self.body_parts['eyes'], intersecting_handler)
                    schedule_chart.add_node(move_eyes)
                    operator_idx += 1

                    move_eyes.execute()

                    self.__draw_all()

                    schedule_chart.add_edge(encode_operator, move_eyes)

                    if previous_motor_eyes_operator is not None:
                        schedule_chart.add_edge(previous_motor_eyes_operator, move_eyes)

                    previous_motor_eyes_operator = move_eyes

                else:
                    # We encoded the handler in time. Update VSTM and LTM.
                    activate_target_location = ActivateTargetLocation(
                        str(operator_idx) + '_activate:' + encode_operator.target.name, self.body_parts['ltm'],
                        current_keyboard, encode_operator.target.name, encode_operator.target)

                    self.compute_duration(schedule_chart)
                    # self.draw_schedule_graph(phrase, schedule_chart)

                    schedule_chart.add_node(activate_target_location)
                    operator_idx += 1

                    activate_target_location.start_time = encode_operator.end_time

                    activate_target_location.execute()

                    if previous_cognitive_operator is not None:
                        schedule_chart.add_edge(previous_cognitive_operator, activate_target_location)

                    schedule_chart.add_edge(encode_operator, activate_target_location)

                    previous_cognitive_operator = activate_target_location

        self.__draw_all()

        perceive_word = Perceptual(str(operator_idx) + '_perceptual:' + 'task', self.body_parts['eyes'])
        perceive_word.duration = perceive_word.duration * len(word)
        perceive_word.execute()
        schedule_chart.add_node(perceive_word)
        operator_idx += 1

        process_word = Cognitive(str(operator_idx) + '_cognitive:' + 'task', None)
        process_word.duration = process_word.duration * len(word)
        process_word.execute()
        schedule_chart.add_node(process_word)
        operator_idx += 1

        if previous_cognitive_operator is not None:
            schedule_chart.add_edge(previous_cognitive_operator, perceive_word)

        schedule_chart.add_edge(perceive_word, process_word)

        if previous_perceptual_operator is not None:
            schedule_chart.add_edge(previous_perceptual_operator, perceive_word)

        if previous_perceptual_word_operator is not None:
            schedule_chart.add_edge(previous_perceptual_word_operator, perceive_word)

        if previous_motor_finger_operator is not None:
            schedule_chart.add_edge(previous_motor_finger_operator, process_word)

        previous_perceptual_word_operator = perceive_word
        previous_perceptual_operator = perceive_word
        previous_cognitive_operator = process_word

        for character in word:
            target = self.handler.find_descendant(character)

            # Locate target using LTM vs. visual search.

            # LTM
            retrieve_target_location = RetrieveTargetLocation(str(operator_idx) + '_retrieve:' + character,
                                                              self.body_parts['ltm'], character)
            operator_idx += 1

            # Before execution retrieval we need to update the current critical path timestamp. The timestamp would be the end time of the previous cognitive operator.

            # self.draw_schedule_graph(phrase, schedule_chart)

            retrieve_target_location.start_time = previous_cognitive_operator.end_time

            current_retrieve_previous_cognitive_operator = previous_cognitive_operator

            retrieve_target_location.execute()

            if retrieve_target_location.device:
                assert(retrieve_target_location.device == current_keyboard)

            # We know the duration of LTM, but we do not add it to the schedule chart until it is shorter than visual search.
            # Instead, start visual search. Any component of the visual search that is less than LTM retrieval will be included in the schedule chart.
            visual_search_duration = 0
            is_found = False
            # TODO
            target_x = target.top_left_x + target.width / 2
            target_y = target.top_left_y + target.height / 2

            if current_keyboard == 'keyboard_1':
                escape_key = self.handler.find_descendant('esc')
            elif current_keyboard == 'keyboard_2':
                escape_key = self.handler.find_descendant('End Show')
            elif current_keyboard == 'keyboard_3':
                escape_key = self.handler.find_descendant('bright-')
            elif current_keyboard == 'keyboard_3':
                escape_key = self.handler.find_descendant('out_4')
            # escape_key.top_left_x = 0
            # escape_key.top_left_y = 0
            # escape_key.width = 0
            # escape_key.height = 0
            move_eyes = Move(str(operator_idx) + '_motor_eyes:' + 'toLeftMost', self.body_parts['eyes'],
                             escape_key)
            move_eyes.execute()
            while not (is_found) and (visual_search_duration < retrieve_target_location.duration):
                # print(retrieve_target_location.duration, " ", visual_search_duration)
                # Move eyes to the phrase.
                # Find which target we intersect with.
                intersecting_event = Event(self.body_parts['eyes'].fixation_x, self.body_parts['eyes'].fixation_y)
                intersecting_handler = self.handler.find_intersect(intersecting_event, current_keyboard)
                if intersecting_handler is not None:
                    # This should always be true; otherwise, we have gone out of the environment.
                    encode_operator = Encode(str(operator_idx) + '_encode:' + intersecting_handler.name,
                                             self.body_parts['eyes'], intersecting_handler)
                    operator_idx += 1

                    # If we find before the any saccade can start, then  simply skip scanning.
                    if retrieve_target_location.duration < encode_operator.t_prep:
                        break

                    encode_operator.execute()
                    visual_search_duration += encode_operator.duration

                    if visual_search_duration >= retrieve_target_location.duration:
                        # if the encoding is taking too long, just end it.
                        break

                    schedule_chart.add_node(encode_operator)

                    schedule_chart.add_edge(previous_cognitive_operator, encode_operator)
                    schedule_chart.add_edge(previous_perceptual_operator, encode_operator)

                    if previous_motor_eyes_operator is not None:
                        schedule_chart.add_edge(previous_motor_eyes_operator, encode_operator)

                    previous_perceptual_operator = encode_operator

                    if encode_operator.initiate_saccade:
                        # We did not encode the handler under the fixation point in time and we need another saccade.
                        move_eyes = Move(str(operator_idx) + '_motor_eyes:' + intersecting_handler.name,
                                         self.body_parts['eyes'], intersecting_handler)
                        schedule_chart.add_node(move_eyes)
                        operator_idx += 1

                        move_eyes.execute()

                        self.__draw_all()

                        visual_search_duration += move_eyes.duration

                        schedule_chart.add_edge(encode_operator, move_eyes)

                        if previous_motor_eyes_operator is not None:
                            schedule_chart.add_edge(previous_motor_eyes_operator, move_eyes)

                        previous_motor_eyes_operator = move_eyes

                    else:
                        # We encoded the handler in time. Update VSTM and LTM.
                        activate_target_location = ActivateTargetLocation(
                            str(operator_idx) + '_activate:' + encode_operator.target.name, self.body_parts['ltm'],
                            current_keyboard, encode_operator.target.name, encode_operator.target)

                        self.compute_duration(schedule_chart)
                        # self.draw_schedule_graph(phrase, schedule_chart)

                        schedule_chart.add_node(activate_target_location)
                        operator_idx += 1

                        activate_target_location.start_time = max(previous_cognitive_operator.end_time,
                                                                  encode_operator.end_time)

                        activate_target_location.execute()

                        visual_search_duration += activate_target_location.duration

                        schedule_chart.add_edge(previous_cognitive_operator, activate_target_location)
                        schedule_chart.add_edge(encode_operator, activate_target_location)

                        previous_cognitive_operator = activate_target_location

                        # Now need to check if this is our target.
                        if encode_operator.target.name == target.name:
                            # We found the target and can move the finger to it.
                            is_found = True
                        else:
                            # This was not what we were looking for. Continue visual search.

                            current_fixation_x = self.body_parts['eyes'].fixation_x
                            current_fixation_y = self.body_parts['eyes'].fixation_y

                            next_fixation_x = 0
                            next_fixation_y = 0

                            # TODO: Implement visual search strategy.
                            # ------------------------------------------------------------------------------------------------------------------------------------

                            next_fixation = None
                            handler_at_next_fixation = None

                            current_position_x = self.body_parts['eyes'].fixation_x
                            current_position_y = self.body_parts['eyes'].fixation_y
                            handle_at_current_fixation = self.handler.find_intersect(Event(current_position_x,
                                                                                current_position_y), current_keyboard)

                            if target.name == '<':
                                key_width = 4.9
                            else:
                                key_width = 30
                            next_fixation_x = current_position_x
                            import random
                            from numpy.random import multivariate_normal
                            findFlag = False
                            while not findFlag:
                                next_fixation_x = next_fixation_x + key_width
                                next_fixation_y = 0

                                handler_at_next_fixation = self.handler.find_intersect(
                                    Event(next_fixation_x, next_fixation_y), current_keyboard)
                                if not handler_at_next_fixation or handler_at_next_fixation.name not in touch_bar_keys:
                                    continue
                                if handle_at_current_fixation.name != handler_at_next_fixation.name or handler_at_next_fixation.name is target.name:
                                    findFlag = True

                            move_eyes = Move(str(operator_idx) + '_motor_eyes:' + handler_at_next_fixation.name,
                                             self.body_parts['eyes'], handler_at_next_fixation)
                            schedule_chart.add_node(move_eyes)
                            operator_idx += 1

                            move_eyes.execute()

                            self.__draw_all()

                            visual_search_duration += move_eyes.duration

                            schedule_chart.add_edge(previous_cognitive_operator, move_eyes)

                            if previous_motor_eyes_operator is not None:
                                schedule_chart.add_edge(previous_motor_eyes_operator, move_eyes)

                            previous_motor_eyes_operator = move_eyes

            move_finger = Move(str(operator_idx) + '_motor_finger:' + character, self.body_parts['thumb'], target)
            schedule_chart.add_node(move_finger)
            operator_idx += 1

            if not is_found:
                # Visual search could not find it before LTM. Add LTM-based congnitive operator to the schedule chart.
                schedule_chart.add_node(retrieve_target_location)

                # self.body_parts['vstm'].put(target.name, retrieve_target_location.symbol_location)

                # Move fixation to the target.
                move_eyes = Move(str(operator_idx) + '_motor_eyes:' + character, self.body_parts['eyes'],
                                 retrieve_target_location.symbol_location)
                schedule_chart.add_node(move_eyes)
                operator_idx += 1

                move_eyes.execute()

                self.__draw_all()

                if current_retrieve_previous_cognitive_operator is not None:
                    schedule_chart.add_edge(current_retrieve_previous_cognitive_operator, retrieve_target_location)

                if previous_cognitive_retrieve_operator is not None:
                    schedule_chart.add_edge(previous_cognitive_retrieve_operator, retrieve_target_location)

                schedule_chart.add_edge(retrieve_target_location, move_eyes)
                schedule_chart.add_edge(retrieve_target_location, move_finger)

                if previous_motor_eyes_operator is not None:
                    schedule_chart.add_edge(previous_motor_eyes_operator, move_eyes)

                previous_cognitive_operator = retrieve_target_location
                previous_cognitive_retrieve_operator = retrieve_target_location

                previous_motor_eyes_operator = move_eyes

                # Find which target we intersect with.
                intersecting_event = Event(self.body_parts['eyes'].fixation_x, self.body_parts['eyes'].fixation_y)
                intersecting_handler = self.handler.find_intersect(intersecting_event, current_keyboard)

                if intersecting_handler is not None:

                    encode_operator = None

                    while encode_operator is None or encode_operator.initiate_saccade:
                        # This should always be true; otherwise, we have gone out of the environment.
                        encode_operator = Encode(str(operator_idx) + '_encode:' + intersecting_handler.name,
                                                 self.body_parts['eyes'], intersecting_handler)
                        schedule_chart.add_node(encode_operator)
                        operator_idx += 1

                        encode_operator.execute()

                        if previous_perceptual_operator is not None:
                            schedule_chart.add_edge(previous_perceptual_operator, encode_operator)

                        if previous_motor_eyes_operator is not None:
                            schedule_chart.add_edge(previous_motor_eyes_operator, encode_operator)

                        previous_perceptual_operator = encode_operator

                        if encode_operator.initiate_saccade:
                            # We did not encode the handler under the fixation point in time and we need another saccade.
                            move_eyes = Move(str(operator_idx) + '_motor_eyes:' + intersecting_handler.name,
                                             self.body_parts['eyes'], intersecting_handler)
                            schedule_chart.add_node(move_eyes)
                            operator_idx += 1

                            move_eyes.execute()

                            self.__draw_all()

                            visual_search_duration += move_eyes.duration

                            schedule_chart.add_edge(encode_operator, move_eyes)

                            if previous_motor_eyes_operator is not None:
                                schedule_chart.add_edge(previous_motor_eyes_operator, move_eyes)

                            previous_motor_eyes_operator = move_eyes

                        else:
                            # We encoded the handler in time. Update VSTM and LTM.
                            activate_target_location = ActivateTargetLocation(
                                str(operator_idx) + '_activate:' + encode_operator.target.name,
                                self.body_parts['ltm'], current_keyboard, encode_operator.target.name,
                                encode_operator.target)

                            self.compute_duration(schedule_chart)
                            # self.draw_schedule_graph(phrase, schedule_chart)

                            schedule_chart.add_node(activate_target_location)
                            operator_idx += 1

                            activate_target_location.start_time = encode_operator.end_time

                            activate_target_location.execute()

                            if previous_cognitive_operator is not None:
                                schedule_chart.add_edge(previous_cognitive_operator, activate_target_location)

                            schedule_chart.add_edge(encode_operator, activate_target_location)

                            previous_cognitive_operator = activate_target_location

            move_finger.execute()
            # change keyboard screen
            if target.name in key2device.keys():
                for keyboard in self.handler.children['touchscreen'].children:
                    if keyboard == current_keyboard:
                        self.handler.children['touchscreen'].children[keyboard].printSwitch = False
                    elif keyboard == key2device[target.name]:
                        self.handler.children['touchscreen'].children[keyboard].printSwitch = True
                        current_keyboard = keyboard
            self.__draw_all()

            if previous_perceptual_operator is not None:
                schedule_chart.add_edge(previous_perceptual_operator, move_finger)

            if previous_cognitive_operator is not None:
                schedule_chart.add_edge(previous_cognitive_operator, move_finger)

            if previous_motor_finger_operator is not None:
                schedule_chart.add_edge(previous_motor_finger_operator, move_finger)

            previous_motor_finger_operator = move_finger

        # Add a dummy operator for easier critical path calculation.
        dummy = OperatorElement('dummy', None)
        if previous_perceptual_operator is not None:
            schedule_chart.add_edge(previous_perceptual_operator, dummy)

        if previous_cognitive_operator is not None:
            schedule_chart.add_edge(previous_cognitive_operator, dummy)

        if previous_motor_finger_operator is not None:
            schedule_chart.add_edge(previous_motor_finger_operator, dummy)

        if previous_motor_eyes_operator is not None:
            schedule_chart.add_edge(previous_motor_eyes_operator, dummy)

        return schedule_chart

    def compute_duration(self, schedule_chart):
        ''' Returns duration of a schedule chart. '''

        duration = 0

        for operator in nx.topological_sort(schedule_chart):

            # Set start time to predecessors max end time.
            operator.start_time = 0
            for predecessor in schedule_chart.predecessors(operator):
                if predecessor.end_time > operator.start_time:
                    operator.start_time = predecessor.end_time

            operator.end_time = operator.start_time + operator.duration

            # Assumes a dummy end operator
            duration = operator.end_time

        return duration

    def draw(self, ax):
        # for body_part in self.body_parts.values():
        # 	body_part.draw(ax)
        pass

    def draw_schedule_graph(self, input, schedule_chart):
        ''' Takes in a schedule graph with already executed nodes, then draws nodes based on their type, start times and duration. '''

        LAYER_HEIGHT = 2000

        max_end_time = 0

        schedule_chart_plot = plt.figure()

        schedule_chart_plot.suptitle(input, fontsize=10)

        ax1 = schedule_chart_plot.add_subplot(111, aspect='equal')

        # Calculate positions.
        for operator in nx.topological_sort(schedule_chart):

            # Split nodes in layers.
            if isinstance(operator, Perceptual):
                if isinstance(operator, Encode):
                    y = 2 * LAYER_HEIGHT
                else:
                    y = LAYER_HEIGHT
            elif isinstance(operator, Cognitive):
                if isinstance(operator, RetrieveTargetLocation):
                    y = 4 * LAYER_HEIGHT
                elif isinstance(operator, ActivateTargetLocation):
                    y = 5 * LAYER_HEIGHT
                else:
                    y = 3 * LAYER_HEIGHT
            elif isinstance(operator, MotorOperator):
                if isinstance(operator.body_part, Eyes):
                    y = 6 * LAYER_HEIGHT
                elif isinstance(operator.body_part, Finger):
                    y = 7 * LAYER_HEIGHT

            ax1.annotate(operator.name, xy=(operator.start_time + operator.duration / 2, y - 3 * LAYER_HEIGHT / 4 - 50),
                         xytext=(0, 0), textcoords="offset points", ha='center', va='center', color='black',
                         weight='bold', clip_on=True, fontsize=4)
            ax1.add_patch(
                patches.Rectangle((operator.start_time, y - 3 * LAYER_HEIGHT / 4), operator.duration, LAYER_HEIGHT / 2,
                                  fill=True, edgecolor='black', facecolor='gray'))

            # Draw arrows from parents.
            for predecessor in schedule_chart.predecessors(operator):
                if isinstance(predecessor, Perceptual):
                    if isinstance(predecessor, Encode):
                        p_y = 2 * LAYER_HEIGHT
                    else:
                        p_y = LAYER_HEIGHT
                elif isinstance(predecessor, Cognitive):
                    if isinstance(predecessor, RetrieveTargetLocation):
                        p_y = 4 * LAYER_HEIGHT
                    elif isinstance(predecessor, ActivateTargetLocation):
                        p_y = 5 * LAYER_HEIGHT
                    else:
                        p_y = 3 * LAYER_HEIGHT
                elif isinstance(predecessor, MotorOperator):
                    if isinstance(predecessor.body_part, Eyes):
                        p_y = 6 * LAYER_HEIGHT
                    elif isinstance(predecessor.body_part, Finger):
                        p_y = 7 * LAYER_HEIGHT

                ax1.add_patch(patches.Arrow(predecessor.end_time, p_y - LAYER_HEIGHT / 2,
                                            operator.start_time - predecessor.end_time,
                                            y - LAYER_HEIGHT / 2 - (p_y - LAYER_HEIGHT / 2), width=50))

            if max_end_time < operator.end_time:
                max_end_time = operator.end_time

        ax1.xaxis.set_ticks(range(0, int(max_end_time) + 1000, 1000))
        ax1.yaxis.set_ticks(range(0, 7 * LAYER_HEIGHT, 1000))

        plt.ylim((0, 7 * LAYER_HEIGHT))
        plt.xlim((0, int(max_end_time) + 1000))
        ax1.set_ylim(ax1.get_ylim()[::-1])

        plt.show(block=True)
        plt.close()

    def __draw_all(self):
        if False:
            #  Visualize the device interface and the position of the thumb.
            device_plot = plt.figure()
            ax1 = device_plot.add_subplot(111, aspect='equal')
            ax1.xaxis.set_ticks(range(self.handler.top_left_x, self.handler.width, 200))
            ax1.yaxis.set_ticks(range(self.handler.top_left_y, self.handler.height, 200))

            self.handler.draw(ax1)
            self.draw(ax1)

            plt.ylim((0, self.handler.height))
            plt.xlim((0, self.handler.width))
            ax1.set_ylim(ax1.get_ylim()[::-1])
            ax1.xaxis.tick_top()

            plt.show(block=True)
            plt.close()

    @staticmethod
    def create_novice(environment):
        human = Human(environment)
        human.create_finger('thumb', 0, 0)
        human.create_eyes('eyes', 0, 0, 1000)
        human.create_ltm('ltm')  # Long term memory
        # human.create_stm('vstm')  # Short term memory

        return human

    @staticmethod
    def create_expert(environment):
        human = Human(environment)
        human.create_finger('thumb', 0, 0)
        human.create_eyes('eyes', 0, 0, 10000)

        # Attach expert LTM.
        expert_store = {}
        expert_ltm_activations = {}

        # expert_ltm_activations[' '] = (0.0, 10000.0)
        # expert_ltm_activations[' '] = 10000.0
        # expert_store[' '] = environment.find_descendant(' ')

        for k in keyboard_1:
            expert_ltm_activations[k] = 10000.0
            expert_store[k] = ('keyboard_1', environment.find_descendant(k))

        for k in keyboard_2:
            expert_ltm_activations[k] = 10000.0
            expert_store[k] = ('keyboard_1', environment.find_descendant(k))

        for k in keyboard_3:
            expert_ltm_activations[k] = 10000.0
            expert_store[k] = ('keyboard_1', environment.find_descendant(k))

        for k in keyboard_4:
            expert_ltm_activations[k] = 10000.0
            expert_store[k] = ('keyboard_1', environment.find_descendant(k))
        # for c in ascii_lowercase:
        #     expert_ltm_activations[c] = (0.0, 10000.0)
        #     expert_store[c] = environment.find_descendant(c)

        human.create_ltm('ltm', store=expert_store, activations=expert_ltm_activations)  # Long term memory

        # human.create_stm('vstm')  # Short term memory

        return human


class BodyPart(ABC):
    ''' This is an abstract class represeting a body part (e.g., fingers, eyes). Body parts can have related body parts that they control (e.g., hand has fingers.)'''

    def __init__(self, name, location_x, location_y, handler=None):
        '''Initialize Body Part with a beginning location and a device that it is acting on (default None)'''
        self.name = name
        self.location_x = location_x
        self.location_y = location_y
        self.parent = None
        self.children = None
        self.handler = handler

    @abstractmethod
    def accept(self, operator):
        raise NotImplementedError("You should implement this!")

    def set_parent(self, parent):
        self.parent = parent
        if not self.parent.children.contains(self):
            self.parent.add_child(self)

    def add_child(self, child):
        if self.children is None:
            self.children = {}
        self.children[child.name] = child

        if not (child.parent == self):
            if child.parent:
                child.parent.remove_child(child)
            child.parent = self

    def remove_child(self, child):
        if child.parent == self:
            if self.children:
                del self.children[child.name]
            child.parent = None

    def draw(self, ax):
        pass


class LongTermMemory(BodyPart):
    def __init__(self, name, store={}, activations={}):
        super(LongTermMemory, self).__init__(name, 0, 0)

        self.store = store  # stores (device, location) pair
        self.activations = activations  # a dictonary of pairs containing last activation time and activation value keyed by symbols they represent.

        # TODO: Initialize LTM parameters.
        self.F = 1.06  # empirical data, scaling factor and thus no unit
        self.f = 1.53  # empirical data, scaling factor and thus no unit
        self.sigma_M = 0.6
        self.d = 0.5  # said to be 0.5 in original paper

    def accept(self, cognitive_operator):
        ''' LTM only accepts cognitive operators. '''

        if not isinstance(cognitive_operator, Cognitive):
            raise Exception('Operator is not a cognitive operator')

        return cognitive_operator.visit_ltm(self)

    def put(self, symbol, device, value):
        ''' Simply updates the activation. This happens instantentiously. '''
        self.store[symbol] = (device, value)
        activation = None

        if symbol in self.activations.keys():
            activation = self.activations[symbol]
            # t = timestamp - activation[0]
            # activation = (timestamp, activation[1] + t**(-self.d))
            activation += 0.5
        else:
            # This is the first time.
            # activation = (timestamp, 0)
            activation = 0

        self.activations[symbol] = activation

        return 0.0

    def get(self, symbol):

        activation = None
        symbol_location = None
        device = None

        if symbol in self.activations.keys():

            device, symbol_location = self.store[symbol]

            scale = (3 ** 0.5) * self.sigma_M / math.pi
            logistic_noise = np.random.logistic(0, scale, 1)
            symbol_location.top_left_x += logistic_noise
            symbol_location.top_left_y += logistic_noise

            activation = self.activations[symbol]
            if activation <= 1:
                self.duration = math.inf
            else:
                self.duration = self.F * (
                            math.e ** (-self.f * math.log(activation)))  # TODO: calculate duration to access LTM.
            duration = self.duration
        else:
            # This is the first time.
            activation = 0

            # Cannot remember what you do not know.
            symbol_location = None
            device = None
            duration = math.inf

        self.activations[symbol] = activation

        return (duration, device, symbol_location)


class ShortTermMemory(BodyPart):
    ''' Short term memory is a FIFO dict with maximum capacity. We do not use decay time in this implementation. The assumption is that if something remains in STM then it is refreshed regularly. '''

    def __init__(self, name, storage_capacity=5):
        super(ShortTermMemory, self).__init__(name, 0, 0)

        self.storage_capacity = storage_capacity

        self.store = OrderedDict()

        self.access_duration = 30.0

    def accept(self, cognitive_operator):
        ''' STM only accepts cognitive operators. '''

        if not isinstance(cognitive_operator, Cognitive):
            raise Exception('Operator is not a cognitive operator')

        return cognitive_operator.visit_stm(self)

    def put(self, symbol, value):
        if len(self.store) > self.storage_capacity:
            # We need to remove the oldest item to make space for the new one.
            oldest = next(iter(self.store))
            del self.store[oldest]

        self.store[symbol] = value

        return self.access_duration

    def get(self, symbol):
        value = None

        if symbol in self.store.keys():
            value = self.store[symbol]
            self.store.move_to_end(symbol, last=False)

        return (self.access_duration, value)

    def contains(self, symbol):
        ''' Utility method to check if STM contains a symbol without updating the STM. '''
        return symbol in self.store.keys()


class Finger(BodyPart):
    ''' Finger model. '''

    def __init__(self, name, location_x, location_y, handler=None):
        super(Finger, self).__init__(name, location_x, location_y, handler)
        self.a = 105.0  # TODO: set your own Fitts' Law parameter a
        self.b = 147.7  # TODO: set your own Fitts' Law parameter b

    def accept(self, motor_operator):
        '''Finger only accepts motor operators.'''
        if not isinstance(motor_operator, MotorOperator):
            raise Exception('Operator is not a motor operator')

        return motor_operator.visit_finger(self)

    def move(self, target):
        ''' Moves the  finger to the new location and returns the duration. '''
        # ---------------------------------------------------------------------------- #

        target_x = target.top_left_x + target.width / 2
        target_y = target.top_left_y + target.height / 2

        A = math.sqrt((self.location_x - target_x) ** 2 + (self.location_y - target_y) ** 2)
        W = min([target.width, target.height])

        duration = self.a + self.b * math.log2(A / W + 1)

        self.location_x = target_x
        self.location_y = target_y

        move_event = MoveBodyPartEvent(self, target_x, 0)
        self.handler.handle(move_event)

        #error touch
        prob = 0.2
        result = np.random.choice(2, p=[prob, 1 - prob])
        while result == 0:
            duration += 100
            prob = prob * prob
            result = np.random.choice(2, p=[prob, 1 - prob])
        return duration


    def visit_interface(self, interface):
        return interface.press()

    def draw(self, ax):
        ax.add_patch(patches.Circle((self.location_x, self.location_y), 10, fill=True))


class Eyes(BodyPart):
    ''' Eyes model. The location is the current fixation point. '''

    def __init__(self, name, location_x, location_y, handler_distance, handler=None):
        ''' Initializes eyes, places them at a specific location at a specific distance from the handler, and sets the fixation point by projecting perpendicular to the handler plane. '''

        super(Eyes, self).__init__(name, location_x, location_y, handler)

        self.handler_distance = handler_distance

        # TODO: Initalize eye movement parameters.
        self.t_sacc = 0.002 * 1000  # should be in [ms]
        self.t_exec = 0.070 * 1000  # should be in [ms]
        self.t_prep = 0.200 * 1000  # should be in [ms]

        self.saccade_noise_sigma = 0.1  # saccade landing-point noise

        self.fixation_x = location_x
        self.fixation_y = location_y

    def accept(self, motor_operator):
        '''Eyes only accepts motor operators.'''
        if not isinstance(motor_operator, MotorOperator):
            raise Exception('Operator is not a motor operator')

        return motor_operator.visit_eyes(self)

    def move(self, target):
        ''' Moves the fixartion point to the new location (performs a saccade) and returns the duration. '''

        target_x = target.top_left_x + target.width / 2
        target_y = target.top_left_y + target.height / 2

        # Convert the gaze into a vector with root at (self.body_part.location_x, self.body_part.location_y, 0).
        current_x_v = self.fixation_x - self.location_x
        current_y_v = self.fixation_y - self.location_y
        current_z_v = self.handler_distance

        # Convert the target gaze into a vector with root at (self.body_part.location_x, self.body_part.location_y, 0).
        target_x_v = target_x - self.location_x
        target_y_v = target_y - self.location_y
        target_z_v = self.handler_distance

        dot_product = current_x_v * target_x_v + current_y_v * target_y_v + current_z_v * target_z_v
        magnitude_current = math.sqrt(current_x_v ** 2 + current_y_v ** 2 + current_z_v ** 2)
        magnitude_target = math.sqrt(target_x_v ** 2 + target_y_v ** 2 + target_z_v ** 2)

        theta = dot_product / (magnitude_current * magnitude_target)

        D = math.acos(theta)

        duration = self.t_prep + self.t_exec + D * self.t_sacc  # TODO: compute duration.

        self.fixation_x = target_x
        self.fixation_y = 0

        # move_event = MoveBodyPartEvent(self, self.fixation_x, self.fixation_y)
        # self.handler.handle(move_event)

        return duration

    def visit_interface(self, interface):
        return interface.see()

    def draw(self, ax):
        ax.add_patch(patches.Circle((self.fixation_x, self.fixation_y), 100, fill=False))
