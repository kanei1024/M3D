import torch.nn as nn
import math, torch
import torch.utils.model_zoo as model_zoo
from torch.nn import init

class Bottleneck(nn.Module):
	expansion = 4

	def __init__(self, inplanes, planes, stride=1, downsample=None):
		super(Bottleneck, self).__init__()
		self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
		self.bn1 = nn.BatchNorm2d(planes)
		self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride,
							   padding=1, bias=False)
		self.bn2 = nn.BatchNorm2d(planes)
		self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1, bias=False)
		self.bn3 = nn.BatchNorm2d(planes * 4)
		self.relu = nn.ReLU(inplace=True)
		self.downsample = downsample
		self.stride = stride

	def forward(self, x):
		residual = x

		out = self.conv1(x)
		out = self.bn1(out)
		out = self.relu(out)

		out = self.conv2(out)
		out = self.bn2(out)
		out = self.relu(out)

		out = self.conv3(out)
		out = self.bn3(out)

		if self.downsample is not None:
			residual = self.downsample(x)

		out += residual
		out = self.relu(out)

		return out


class ResNet(nn.Module):

	def __init__(self, block, layers, num_classes=1000, train=True):
		self.inplanes = 64
		super(ResNet, self).__init__()
		self.istrain = train

		self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
		self.bn1 = nn.BatchNorm2d(64)
		self.relu = nn.ReLU(inplace=True)
		self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
		self.layer1 = self._make_layer(block, 64, layers[0])
		self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
		self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
		self.layer4 = self._make_layer(block, 512, layers[3], stride=1)
		self.avgpool = nn.AvgPool2d((16,8), stride=1)

		self.num_features = 128
		self.feat = nn.Linear(512 * block.expansion, self.num_features)
		self.feat_bn = nn.BatchNorm1d(self.num_features)
		init.kaiming_normal(self.feat.weight, mode='fan_out')
		init.constant(self.feat.bias, 0)
		init.constant(self.feat_bn.weight, 1)
		init.constant(self.feat_bn.bias, 0)
		self.drop = nn.Dropout(0.5)
		self.classifier = nn.Linear(self.num_features, num_classes)
		init.normal(self.classifier.weight, std=0.001)
	 	init.constant(self.classifier.bias, 0)

		for m in self.modules():
			if isinstance(m, nn.Conv2d):
				n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
				m.weight.data.normal_(0, math.sqrt(2. / n))
			elif isinstance(m, nn.BatchNorm2d):
				m.weight.data.fill_(1)
				m.bias.data.zero_()

	def _make_layer(self, block, planes, blocks, stride=1):
		downsample = None
		if stride != 1 or self.inplanes != planes * block.expansion:
			downsample = nn.Sequential(
				nn.Conv2d(self.inplanes, planes * block.expansion,
						  kernel_size=1, stride=stride, bias=False),
				nn.BatchNorm2d(planes * block.expansion),
			)

		layers = []
		layers.append(block(self.inplanes, planes, stride, downsample))
		self.inplanes = planes * block.expansion
		for i in range(1, blocks):
			layers.append(block(self.inplanes, planes))

		return nn.Sequential(*layers)

	def forward(self, x):
		x = self.conv1(x)
		x = self.bn1(x)
		x = self.relu(x)
		x = self.maxpool(x)

		x = self.layer1(x)
		x = self.layer2(x)
		x = self.layer3(x)
		x = self.layer4(x)

		x = self.avgpool(x)
		x = x.view(x.size(0), -1)
		x = self.feat(x)

		if self.istrain:
			x = self.feat_bn(x)
			x = self.relu(x)
			x = self.drop(x)
			x = self.classifier(x)
		return x

def resnet50(pretrained='True', num_classes=1000, train=True):
	model = ResNet(Bottleneck, [3, 4, 6, 3], num_classes, train)
	#if pretrained:
	#	model.load_state_dict('resnet50-19c8e357.pth')
	weight = torch.load(pretrained)
	static = model.state_dict()
	for name, param in weight.items():
		if name not in static:
			print 'not load weight ', name
			continue
		if isinstance(param, nn.Parameter):
			print 'load weight ', name, type(param)
			param = param.data
			static[name].copy_(param)
	#model.load_state_dict(weight)
	return model
