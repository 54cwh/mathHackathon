def composite_fitness(survival, prey_capture, escape_success, energy_efficiency):
    return 0.35 * survival + 0.25 * prey_capture + 0.20 * escape_success + 0.20 * energy_efficiency


def edge_distance(a, b):
    return (a != b).float().mean().item()


def tau_distance(a, b):
    return (a - b).abs().mean().item()
