from abc import ABC, abstractmethod
from typing import Callable

class PreProcessingTask(ABC):
    """Abstract base class for data processing steps."""

    @abstractmethod
    def execute(self, data):
        """Processes the data and returns the output."""
        pass

class CleaningTask(PreProcessingTask):
    def __init__(self, clean_function: Callable[[str], str]):
        self.clean_function = clean_function

    def execute(self, data):
        return data.apply(self.clean_function)

class FilteringTask(PreProcessingTask):
    def __init__(self, filter_function: Callable[[any], bool]):
        self.filter_function = filter_function

    def execute(self, data):
        return data[self.filter_function(data)]

class FormattingTask(PreProcessingTask):
    def __init__(self, format_function: Callable[[any], str]):
        self.format_function = format_function

    def execute(self, data):
        return data.apply(self.format_function)

class ColumnFilteringTask(PreProcessingTask):
    def __init__(self, columns_to_keep: [str]):
        self.columns_to_keep = columns_to_keep

    def execute(self, data):
        return data[self.columns_to_keep]

class PreProcessingPipeline:
    def __init__(self, tasks: [PreProcessingTask]):
        self.tasks = tasks

    def run(self, data):
        """Runs the pipeline and returns the processed data."""
        for processor in self.tasks:
            data = processor.process(data)
        return data

def read_filter_pipeline(yaml_file_path:str):
    # import configparser

    # config = configparser.ConfigParser()
    # config.read(yaml_file_path)
    
    import yaml

    with open(yaml_file_path) as f:
        config = yaml.safe_load(f)
    
    filtering_criteria = dict(config["filtering_criteria"])

    return filtering_criteria

def apply_filter_pipeline(df, filter_pipeline):

    columns = filter_pipeline["columns"]
    conditions = filter_pipeline["conditions"]

    print(f"------ columns ------ \n {columns}")
    print(f"------ conditions ------ \n {conditions}")

    mask = True

    for column, cond_dict in zip(columns, conditions):
        print(column, cond_dict[column])
        condition = cond_dict[column]
        print(condition)
        operator = condition["operator"]
        value = condition["value"]
        operand_type = condition["operand_type"]

        if operator == ">":
            if operand_type == "col":
                mask &= df[column] > df[value]
            else:
                mask &= df[column] > value
        elif operator == "<":
            if operand_type == "col":
                mask &= df[column] < df[value]
            else:
                mask &= df[column] < value
        elif operator == "==":
            if operand_type == "col":
                mask &= df[column] == df[value]
            else:
                mask &= df[column] == value
        elif operator == "!=":
            if operand_type == "col":
                mask &= df[column] != df[value]
            else:
                mask &= df[column] != value
        elif operator == "in":
            if operand_type == "col":
                mask &= df[column].isin(df[value])
            else:
                mask &= df[column].isin(value)
        elif operator == "not in":
            if operand_type == "col":
                mask &= ~df[column].isin(df[value])
            else:
                mask &= ~df[column].isin(value)

    filtered_df = df[mask]

    return filtered_df


####--------------------------- example code ----------------------------####

# Define functions for each step
def remove_whitespace(text):
    return text.str.strip()

def filter_greater_than_20(data):
    return data["numerical_data"] > 20

def format_to_two_decimals(value):
    return f"{value:.2f}"

# Create sample data
data = {
    "text": ["This is a sample text.", "This is another sample text.", "This is the third sample text."],
    "numerical_data": [10, 20, 30]
}

# Load data into a pandas DataFrame
import os
import pandas as pd
df = pd.DataFrame(data)

DATA_DIR = "~/source_code/HFT-Options-EIS-Global/datasets/theta/"
bn_data_path = os.path.join(DATA_DIR,"BANKNIFTY_20230227_Intraday.csv")
spx_data_path = os.path.join(DATA_DIR,"SPXW_20230227_Intraday.csv")

df_bn = pd.read_csv(bn_data_path)
df_spx = pd.read_csv(spx_data_path)


# read filter pipeline
print(f"\n {df_spx}")
print(read_filter_pipeline('preproc_pipeline.yaml'))
df = apply_filter_pipeline(df_spx, read_filter_pipeline('preproc_pipeline.yaml'))
print(f"\n {df}")
# Create processor instances using dependency injection
# clean_processor = CleaningTask(clean_function=lambda x: x.strip() if type(x) == "<class 'str'>" else x)
# filter_processor = FilteringTask(filter_function=filter_greater_than_20)
# format_processor = FormattingTask(format_function=format_to_two_decimals)

# columns_to_keep = ["text", "numerical_data"]
# column_filter_processor = ColumnFilteringTask(columns_to_keep)

# # Define the pipeline
# pipeline = PreProcessingPipeline([clean_processor, 
#                                    filter_processor, 
#                                    format_processor,
#                                    column_filter_processor
#                                    ])

# # Run the pipeline and process data
# processed_data = pipeline.run(df)

# # Save the processed data
# processed_data.to_csv("output.csv", index=False)

# print("Data processing completed successfully!")
