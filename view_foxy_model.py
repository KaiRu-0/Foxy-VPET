import torch

checkpoint = torch.load("foxy_model/model.pth", map_location="cpu")
policy_net = checkpoint['policy_net']

# Extract final layer
weights = policy_net['fc3.weight']  # shape: [num_actions, hidden_size]
biases = policy_net['fc3.bias']     # shape: [num_actions]

actions = ['excited', 'relax', 'sleep', 'walk']

print("=== Action Weights (last layer) ===")
for i, action in enumerate(actions):
	print(f"\nAction: {action}")
	print(f"Bias: {biases[i].item():.4f}")
	# To avoid printing huge vectors, just show stats
	print(f"Weight shape: {weights[i].shape}")
	print(f"  min={weights[i].min().item():.4f}, max={weights[i].max().item():.4f}, mean={weights[i].mean().item():.4f}")
