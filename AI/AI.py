import torch
import torch.nn as nn
import torch.nn.functional as f
import pandas

class Model(nn.Module):
    # input layer = 4 features of the flower --> hidden (some number) --> H2(n) --> output(3 classes of flowers)
    def __init__(self, inputs=4, outputs=3,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fc1 = nn.Linear(inputs, 128) # fc stands for fully connected refering to all the connected nodes
        self.fc2 = nn.Linear(128, 64) # moving data along to the next hidden layer of neurons
        self.fc3 = nn.Linear(64, outputs)

    def move_forward(self, data):
        data = f.relu(self.fc1(data)) # moving through the first layer of the neural net
        data = f.relu(self.fc2(data))
        data = f.relu(self.fc3(data))

        return data

torch.manual_seed(41)

model = Model()