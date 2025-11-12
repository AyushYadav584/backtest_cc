from abc import ABC, abstractmethod

class DataProcessingHandler(ABC):
    def __init__(self, successor=None):
        self.successor = successor

    @abstractmethod
    def handle(self, data):
        pass

class CleaningHandler(DataProcessingHandler):
    def __init__(self, clean_function):
        super().__init__()
        self.clean_function = clean_function

    def handle(self, data):
        cleaned_data = data.apply(self.clean_function)
        if self.successor:
            return self.successor.handle(cleaned_data)
        return cleaned_data

class RowFilteringHandler(DataProcessingHandler):
    def __init__(self, filter_function):
        super().__init__()
        self.filter_function = filter_function

    def handle(self, data):
        filtered_data = data[self.filter_function(data)]
        if self.successor:
            return self.successor.handle(filtered_data)
        return filtered_data

class ColFilteringHandler(DataProcessingHandler):
    def __init__(self, filter_function):
        super().__init__()
        self.filter_function = filter_function

    def handle(self, data):
        filtered_data = data[self.filter_function(data)]
        if self.successor:
            return self.successor.handle(filtered_data)
        return filtered_data

class FormattingHandler(DataProcessingHandler):
    def __init__(self, format_function):
        super().__init__()
        self.format_function = format_function

    def handle(self, data):
        formatted_data = data.apply(self.format_function)
        if self.successor:
            return self.successor.handle(formatted_data)
        return formatted_data

# Define the initial handler
remove_whitespace_handler = CleaningHandler(lambda x: x.strip())

# Chain the handlers
filter_greater_than_20_handler = RowFilteringHandler(lambda x: x["numerical_data"] > 20)
format_to_two_decimals_handler = FormattingHandler(lambda x: f"{x:.2f}")

remove_whitespace_handler.successor = filter_greater_than_20_handler
filter_greater_than_20_handler.successor = format_to_two_decimals_handler

# Start processing data
processed_data = remove_whitespace_handler.handle(df)

# Save the processed data
processed_data.to_csv("output.csv", index=False)

print("Data processing completed successfully!")
