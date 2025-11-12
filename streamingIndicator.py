import numpy as np

class StreamingIndicator(object):
    """
    A class to represent a streaming indicator that calculates techincal indicators over a specified window size.
    Attributes:
    data (numpy.ndarray): An array to store the values within the window.
    index (int): The current index in the window.
    count (int): The number of values added to the window.
    sum (float): The sum of the values within the window.
    Methods:
    __init__(window_size):
        Initializes the StreamingIndicator with a specified window size.
    add(value):
        Adds a new value to the window and updates the SMA calculation.
    get():
        Returns the current SMA value.

    
    Implemented: SMA, 
    """

    def __init__(self, window_size):
        """
        Initializes the StreamingIndicator with a specified window size.
        
        Parameters:
        window_size (int): The size of the window for which the SMA is calculated.
        """
        self.window_size = window_size
        self.data = np.zeros(window_size)
        self.index = 0
        self.count = 0
        self.sum = 0.0

    def add(self, value):
        pass
    
    def get(self):
        pass

        

class StreamingSMA(StreamingIndicator):
    """
    A class to calculate the Simple Moving Average (SMA) for a stream of data using a ring buffer.
    
    Attributes:
    window_size (int): The size of the window for which the SMA is calculated.
    data (np.ndarray): The ring buffer to store the data points.
    index (int): The current index in the ring buffer.
    count (int): The number of data points added.
    sum (float): The sum of the data points in the current window.
    """
    
    def __init__(self, window_size):
       super().__init__(window_size)
    

    def add(self, value):
        """
        Adds a new value to the stream and updates the SMA.
        
        Parameters:
        value (float): The new value to be added to the stream.
        
        Returns:
        float: The updated SMA after adding the new value.
        """
        if self.count < self.window_size:
            self.count += 1
        else:
            self.sum -= self.data[self.index]
        
        self.data[self.index] = value
        self.sum += value
        self.index = (self.index + 1) % self.window_size
        return self.get()

    def get(self):
        """
        Calculates the current SMA.
        
        Returns:
        float: The current SMA.
        """
        if self.count == 0:
            return 0
        return self.sum / self.count

# Example usage:
if __name__ == "__main__":
    sma5 = StreamingSMA(window_size=5)
    print(sma5.add(1))  # Add value 1 and print the updated SMA
    print(sma5.add(2))  # Add value 2 and print the updated SMA
    print(sma5.add(3))  # Add value 3 and print the updated SMA
    print(sma5.add(4))  # Add value 4 and print the updated SMA
    print(sma5.add(5))  # Add value 5 and print the updated SMA
    print(sma5.add(6))  # Add value 6 and print the updated SMA
    print('\n')
    sma15 = StreamingSMA(window_size=15)
    print(sma15.add(1))  # Add value 1 and print the updated SMA
    print(sma15.add(2))  # Add value 2 and print the updated SMA
    print(sma15.add(3))  # Add value 3 and print the updated SMA
    print(sma15.add(4))  # Add value 4 and print the updated SMA
    print(sma15.add(5))  # Add value 5 and print the updated SMA
    print(sma15.add(6))  # Add value 6 and print the updated SMA
