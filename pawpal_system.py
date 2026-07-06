class Owner:
    def __init__(self, name):
        self.name = name
        self.pets = []

    def add_pet(self, pet):
        self.pets.append(pet)

    def remove_pet(self, pet_id):
        self.pets = [pet for pet in self.pets if pet.id != pet_id]


class Pet:
    def __init__(self, pet_id, name, species, age):
        self.id = pet_id
        self.name = name
        self.species = species
        self.age = age
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task_id):
        self.tasks = [task for task in self.tasks if task.id != task_id]


class Task:
    def __init__(self, task_id, name, duration_minutes, priority="medium", recurring=False):
        self.id = task_id
        self.name = name
        self.duration_minutes = duration_minutes
        self.priority = priority
        self.recurring = recurring

    def estimate_score(self):
        priority_scores = {"low": 1, "medium": 2, "high": 3}
        return priority_scores.get(self.priority, 2) * self.duration_minutes


class Schedule:
    def __init__(self, date):
        self.date = date
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task_id):
        self.tasks = [task for task in self.tasks if task.id != task_id]

    def total_duration(self):
        return sum(task.duration_minutes for task in self.tasks)
