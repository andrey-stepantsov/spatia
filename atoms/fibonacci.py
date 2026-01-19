# settings: standard
# anchor: 100 100
# intent: Demonstrate a simple recursive vs iterative algorithm

def fibonacci_recursive(n):
    """
    Calculates the nth Fibonacci number recursively.
    O(2^n) complexity.
    """
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)

def fibonacci_iterative(n):
    """
    Calculates the nth Fibonacci number iteratively.
    O(n) complexity.
    """
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

if __name__ == "__main__":
    n = 10
    print(f"Recursive({n}): {fibonacci_recursive(n)}")
    print(f"Iterative({n}): {fibonacci_iterative(n)}")
