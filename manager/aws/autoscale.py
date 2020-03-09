import atexit
import datetime
import math
import sys

import numpy as np
from apscheduler.schedulers.background import BackgroundScheduler

import manager
from manager.aws import autoscale, instance_manager


class AutoScaler():

    def __init__(self, ec2_manager):
        self.ec2_manager = ec2_manager
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        atexit.register(lambda: self.scheduler.shutdown())

    def auto_scale(self):  # 2 MINUTES
        # check CPU utilization for last 2 minutes / every 1 minute,
        instances = self.ec2_manager.get_instances(live_only=True)
        cpu_usage_data = self.ec2_manager.get_cpu_utilization(k=2)
        cpu_avg = np.mean(cpu_usage_data)

        if cpu_avg >= 70:
            increase_pool = math.ceil(
                len(instances)*cpu_avg/50 - len(instances))
            self.scale_up(k=increase_pool)
            print("increase", increase_pool)

        if cpu_avg <= 30:
            decrease_pool = int(len(instances) - len(instances)*cpu_avg/50)
            self.scale_down(k=decrease_pool)
            print("decrease", decrease_pool)

    def scale_up(self, k=1):
        instances = self.ec2_manager.launch_instances(k)
        self.scheduler.add_job(
            func=lambda: self.ec2_manager.register_instances_elb(
                [instance['InstanceId'] for instance in instances]),
            trigger='date',
            run_date=datetime.datetime.now() + datetime.timedelta(seconds=120))
        return instances

    def scale_down(self, k=1):
        instances = self.ec2_manager.get_instances(live_only=True)

        assert len(instances) > k, 'k is more than number of instances'
        instances_to_terminated = [instance['InstanceId']
                                   for instance in instances[:k]]

        self.ec2_manager.unregister_instances_elb(instances_to_terminated)
        self.ec2_manager.terminate_instances(instances_to_terminated)
