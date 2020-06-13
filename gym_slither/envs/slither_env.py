import math
import os
import signal
import sys
import time
from os import path
from io import BytesIO
from time import sleep
import numpy as np
from PIL import Image
from requests import get
from random import randint
from subprocess import Popen
import gym
from gym import error, spaces, utils
from gym.utils import seeding
import matplotlib.pyplot as plt

CWD = path.dirname(path.abspath(__file__))

class SlitherEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, render, idx, use_angle_delta, past_frames=4, xvfb=False):
        self.process = None
        self.window = render
        self.idx = idx
        self.angle = 0
        self.done = False
        self.use_angle_delta = use_angle_delta
        self.img = None
        self.state = None
        self.xvfb = xvfb
        self.past_frames = past_frames
        self.last_states = [np.zeros((128,128))] * past_frames

        self.action_space = spaces.Tuple((
            spaces.Box(low=-1, high=1, dtype=np.float32),
            spaces.Discrete(2)
        ))
        self.observation_space = spaces.Box(low=0, high=255, shape=
                    (128, 128), dtype=np.uint8)

    def reset(self):
        if not self.process or not self.done:
            if self.process:
                self.quit()
            self.port = str(randint(3001, 9999))
            self.path = "http://localhost:" + self.port
            cmd = f"electron --ignore-gpu-blacklist app -p {self.port} -i {self.idx}"
            if self.window:
                cmd += " -w"
            if self.xvfb:
                cmd = "xvfb-maybe " + cmd
            self.process = Popen(cmd, shell=True, cwd=CWD)
            print("start electron")
        else:
            while self.ready():
                sleep(0.1)

        self.done = False
        self.state = None
        self.score = 10.0
        self.last_score = 10.0
        self.last_states = [np.zeros((128,128))] * self.past_frames

        # hang until ready
        ready = False
        for _ in range(100):
            if not self.is_alive():
                break
            if not self.ready():
                sleep(0.1)
            else:
                ready = True
                break
        if not ready:
            self.process = None
            return self.reset()

        return self.get_state(0)

    def is_alive(self):
        if self.process is None:
            return False
        if self.process.poll() is not None:
            self.process = None
            return False
        return True

    def request(self, url):
        if not self.is_alive():
            print("electron dead")
            return None

        response = None
        try:
            response = get(url, timeout=0.5)
        except:
            #print("Unexpected error:", sys.exc_info()[0])
            pass
        return response

    def quit(self):
        Popen("TASKKILL /F /PID {pid} /T".format(pid=self.process.pid))
        self.process = None

    def ready(self):
        #print("ready?")
        status = self.request(self.path + "/ready")
        if status is None:
            return False
        return status.text == "true"

    def compute_reward(self, score):
        reward = score - self.last_score
        self.last_score = score
        return reward

    def step(self, act=(0, 0)):
        ts = time.time()

        speed = 1 if act[0] > 0 else 0
        angle = act[1]
        if self.use_angle_delta:
            angle += self.get_angle()
        pos_x = 50 * math.cos(angle)
        pos_y = 50 * math.sin(angle)
        self.move_mouse(pos_x, pos_y, speed)

        time.sleep(0.2)

        state = self.get_state(ts)
        done = self.is_over()
        score = self.get_score()
        reward = self.compute_reward(score)

        #reward += 0.2
        #reward = (self.get_width() - 1) * 100.0

        # if speed and score < 15:
        #     reward -= 1
        if done:
            reward = -30
        print(act, reward)

        # sys.stdout.write(f"\rts: {ts}; reward:{reward}            ")
        # sys.stdout.flush()
        return state, reward, done, {'ts': ts, 'score': score}

    def step2(self, act=(0, 0)): #use the snake's width as the reward
        ts = time.time()
        done = self.is_over()
        score = self.get_score()
        state = self.get_state(ts)

        if done:
            reward = -50

        speed = act[0]
        angle = act[1]
        if self.use_angle_delta:
            angle += self.get_angle()
        pos_x = 50 * math.cos(angle)
        pos_y = 50 * math.sin(angle)
        self.move_mouse(pos_x, pos_y, speed)

        reward = (self.get_width() - 1)*100.0
        print(f"reward: {reward}")
        return state, reward, done, {ts: ts}

    def is_over(self):
        if not self.done:
            response = self.request(self.path + "/done")
            if response is not None:
                self.done = response.text == "true"
        return self.done

    def get_state(self, ts):
        if not self.done:
            response = self.request(self.path + "/state")
            if response is None:
                return self.state
            angle = float(response.headers['snake-angle'])
            im = Image.open(BytesIO(response.content)).convert('L')
            if self.use_angle_delta:
                im = im.rotate(angle / math.pi * 180.0 + 90, fillcolor=0)
            width, height = im.size  # Get dimensions
            center_x = width / 2
            center_y = height / 2
            width = 128
            height = 128
            cropped = im.crop((center_x - width/2, center_y - height/2, center_x + width/2, center_y + height/2))

            # im.thumbnail((128, 128))
            # im.save(f"./latest_ddpg/{ts}.png")
            state = np.array(cropped)
            # print(response.content)
            # state[state < 50] = 0

            # cropped = Image.fromarray(state)
            # if not self.img:
            #     self.img = plt.imshow(cropped)
            #     plt.ion()
            #     plt.show()
            # else:
            #     self.img.set_data(cropped)
            #     plt.draw()
            #     plt.pause(0.000000001)

            # state = state/ 255.0
            self.last_states.append(state)
            if len(self.last_states) > self.past_frames:
                self.last_states = self.last_states[1:]
            self.state = np.stack(self.last_states, axis=0)
            # self.state = state
        assert type(self.state) != type(False)
        return self.state

    def get_angle(self):
        if not self.done:
            response = self.request(self.path + "/angle")
            if response is not None:
                self.angle = np.float32(response.text)
            else:
                return self.angle
        return self.angle

    def get_score(self):
        if not self.done:
            response = self.request(self.path + "/score")
            if response is not None:
                self.score = float(response.text)
            else:
                return self.score
        return self.score

    def get_width(self):
        if not self.done:
            response = self.request(self.path + "/snake-width")
            self.width = float(response.text)
        return self.width

    def move_mouse(self, x, y, hold):
        if not self.done:
            self.request(f"{self.path}/mouse/{x:.2f}/{y:.2f}/{hold}")

    def get_mouse(self):
        response = self.request(self.path + "/get-mouse")
        x, y, hold, cur_angle = response.text.split(",")
        x = float(x)
        y = float(y)
        cur_angle = float(cur_angle)
        hold = int(hold)
        angle = math.atan2(y - 0.5, x - 0.5)
        # print(hold, x, y, cur_angle, angle)
        return [hold, angle - cur_angle]

    # def do_action(self, action):
    #     if action > 1.0: action = 1.0
    #     if action < -1.0: action = -1.0
    #     command = "left" if action < 0 else "right"
    #     duration = str(int(abs(action * 1000.0)))
    #     request(self.path + "/action/" + command + "/" + duration)

    def render(self, mode='human'):
        pass
    
    def close(self):
        if self.process:
            self.quit()