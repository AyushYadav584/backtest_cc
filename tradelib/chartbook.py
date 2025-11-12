import warnings
warnings.filterwarnings('ignore')

import os, shutil
import aspose.words as aw
import dataframe_image as dfi

from fpdf import FPDF
from PIL import Image
from datetime import date
from tradelib.tradelib_global_constants import *
from pdfrw import PdfReader, PdfWriter, PageMerge
from option_trading_plots import Chartpack

# with open('/home/cloudcraftz/Desktop/leatest-backtest-multi/HFT-Options-EIS-Global/output_dir.txt', 'r') as file:
#     output_dir_folder = file.read()

output_dir_folder = output_dir_folder

path_to_folder = os.path.join(output_dir_folder, "consolidated_store")
chtpck = Chartpack(filepath= path_to_folder , name = custom_strategy_name,
                   asset_class=asset_class, underlying=underlying, \
                   startMonth=month_mapper[start_date.month], startYear=start_date.year, \
                   endMonth=month_mapper[end_date.month], endYear=end_date.year
                )

# make report directory
os.makedirs("Report", exist_ok=True)
underlying_folder_name = underlying

# report path
os.makedirs(f'Report/{underlying_folder_name}', exist_ok = True)
image_path = f'Report/{underlying_folder_name}'

# chart generation
meta_data = chtpck.meta_data_table(title=chart_title)
dfi.export(meta_data, f'{image_path}/meta_data.png')

technical_summary = chtpck.technical_summary()
dfi.export(technical_summary, f'{image_path}/tech_summary.png')

desc_stats = chtpck.generate_descriptive_stats()
dfi.export(desc_stats, f'{image_path}/desc_stats.png')

portfolio_growth_fig = chtpck.plot_port_value()
portfolio_growth_fig.write_image(f'{image_path}/portfolio_growth_fig.png')

gainloss_from_mean_fig = chtpck.gainloss_from_mean()
gainloss_from_mean_fig.write_image(f'{image_path}/gainloss_from_mean_fig.png')

max_drawdown_fig = chtpck.max_drawdown()
max_drawdown_fig.write_image(f'{image_path}/max_drawdown_fig.png')

winnning_losing_fig = chtpck.winnning_losing_()
winnning_losing_fig.write_image(f'{image_path}/winnning_losing_fig.png')

plot_rolling_std_fig = chtpck.plot_rolling_std()
plot_rolling_std_fig.write_image(f'{image_path}/plot_rolling_std_fig.png')

winlossratio_0 = chtpck.winlossratio()[0]
winlossratio_0.write_image(f'{image_path}/winlossratio_0.png')

winlossratio_1 = chtpck.winlossratio()[1]
winlossratio_1.write_image(f'{image_path}/winlossratio_1.png')

rolling_ratio = chtpck.rolling_ratio()
rolling_ratio.write_image(f'{image_path}/rolling_ratio.png')

daily_gain_distribution = chtpck.distribution_plots()
daily_gain_distribution.write_image(f'{image_path}/daily_gain_distribution.png')

weekly_gain_distribution = chtpck.distribution_plots(freq='W')
weekly_gain_distribution.write_image(f'{image_path}/weekly_gain_distribution.png')

realized_vol = chtpck.plot_realized_vol()
realized_vol.write_image(f'{image_path}/realized_vol.png')

imp_real_vol = chtpck.plot_realized_implied_vol(window=15)
imp_real_vol.write_image(f'{image_path}/realized_imp_vol.png')

if strategy_to_execute == 'CONSTANT_RISK_CONDOR_STRATEGY':
    risk_chart = chtpck.risk_chart_plots(log_file_path=output_dir_folder)
    risk_chart.write_image(f'{image_path}/risk_chart.png')

## Addition
# plot_by_trade_taken_day_1 = chtpck.plot_by_trade_taken_day()[1]
# plot_by_trade_taken_day_1.write_image(f'{image_path}/pnl_by_tt_1.png')

# plot_realized_implied_vol_port_wk = chtpck.plot_realized_implied_vol_port()
# plot_realized_implied_vol_port_wk.write_image(f'{image_path}/imp_real_pnl.png')

# plot_vol_spread_change_pnl_wk = chtpck.plot_vol_spread_change_pnl()
# plot_vol_spread_change_pnl_wk.write_image(f'{image_path}/imp_real_pnl_ch_spread.png')

# plot_vol_spread_pnl_trades_taken_wk = chtpck.plot_vol_spread_pnl_trades_taken()
# plot_vol_spread_pnl_trades_taken_wk.write_image(f'{image_path}/plot_vol_spread_tt.png')

plot_monthly_level_pnl = chtpck.monthly_pnl_plot()
plot_monthly_level_pnl.write_image(f'{image_path}/monthly_level_pnl.png')

## End

port_delta = chtpck.plot_port_delta()
port_delta.write_image(f'{image_path}/portfolio_delta.png')

weekly_pnl = chtpck.plot_weekly_pnl()
weekly_pnl.write_image(f'{image_path}/weekly_pnl.png')

avg_pnl_per_trade_day = chtpck.average_pnl_per_trading_day()
avg_pnl_per_trade_day.write_image(f'{image_path}/avg_pnl_per_trade_day.png')


# PDF generation code
BASE_PATH = 'Report/'
PDF_PATH = 'PDF/'

PATH = os.path.join(BASE_PATH, underlying_folder_name)

start, end = (month_mapper[start_date.month] + "-" + str(start_date.year)), (month_mapper[end_date.month] + "-" + str(end_date.year))
PDF_NAME = underlying_folder_name + "_" + start + "_" + end + "_" + custom_strategy_name

# chart filepaths
PDF_PATH = os.path.join(BASE_PATH, PDF_PATH)

if strategy_to_execute == 'CONSTANT_RISK_CONDOR_STRATEGY':

    FILENAMES = [f'{PATH}/meta_data.png', f"{PATH}/empty.png", f"{PATH}/tech_summary.png",\
                f"{PATH}/empty.png", f"{PATH}/desc_stats.png", f"{PATH}/empty.png",
                f'{PATH}/portfolio_growth_fig.png', f'{PATH}/max_drawdown_fig.png', \
                f'{PATH}/plot_rolling_std_fig.png', f'{PATH}/weekly_pnl.png', f'{PATH}/gainloss_from_mean_fig.png', \
                f'{PATH}/realized_vol.png', f'{PATH}/realized_imp_vol.png', 
                f'{PATH}/risk_chart.png',
                # f'{PATH}/pnl_by_tt_1.png', 
                # f'{PATH}/imp_real_pnl.png', \
                # f'{PATH}/imp_real_pnl_ch_spread.png', \
                # f'{PATH}/plot_vol_spread_tt.png', \
                f'{PATH}/winnning_losing_fig.png', \
                f'{PATH}/winlossratio_1.png', f'{PATH}/daily_gain_distribution.png', \
                f'{PATH}/weekly_gain_distribution.png',
                f'{PATH}/avg_pnl_per_trade_day.png',
                f'{PATH}/winlossratio_0.png', f'{PATH}/rolling_ratio.png',
                f'{PATH}/portfolio_delta.png',
                f'{PATH}/monthly_level_pnl.png'
                ]

else:
    FILENAMES = [f'{PATH}/meta_data.png', f"{PATH}/empty.png", f"{PATH}/tech_summary.png",\
                f"{PATH}/empty.png", f"{PATH}/desc_stats.png", f"{PATH}/empty.png",
                f'{PATH}/portfolio_growth_fig.png', f'{PATH}/max_drawdown_fig.png', \
                f'{PATH}/plot_rolling_std_fig.png', f'{PATH}/weekly_pnl.png', f'{PATH}/gainloss_from_mean_fig.png', \
                f'{PATH}/realized_vol.png', f'{PATH}/realized_imp_vol.png', 
                # f'{PATH}/pnl_by_tt_1.png', 
                # f'{PATH}/imp_real_pnl.png', \
                # f'{PATH}/imp_real_pnl_ch_spread.png', \
                # f'{PATH}/plot_vol_spread_tt.png', \
                f'{PATH}/winnning_losing_fig.png', \
                f'{PATH}/winlossratio_1.png', f'{PATH}/daily_gain_distribution.png', \
                f'{PATH}/weekly_gain_distribution.png',
                f'{PATH}/avg_pnl_per_trade_day.png',
                f'{PATH}/winlossratio_0.png', f'{PATH}/rolling_ratio.png',
                f'{PATH}/portfolio_delta.png',
                f'{PATH}/monthly_level_pnl.png'
                ]

from PIL import Image

def pdf_generator(fileNames, pdf_path, pdf_name):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    max_width, max_height = 210, 297  # A4 size in mm
    margin = 10
    first_page_top_margin = 50  # Space for logo/header on first page

    pdf.add_page()
    y_cursor = first_page_top_margin

    for i, image_file in enumerate(fileNames):
        try:
            image = Image.open(image_file)
            width_px, height_px = image.size

            # Convert pixels to mm
            width_mm = width_px * 0.264583
            height_mm = height_px * 0.264583

            # Scale image if too wide
            if width_mm > (max_width - 2 * margin):
                scale = (max_width - 2 * margin) / width_mm
                width_mm *= scale
                height_mm *= scale

            # If image doesn't fit on current page, go to next page
            if y_cursor + height_mm > (max_height - margin):
                pdf.add_page()
                y_cursor = margin  # normal margin from second page onwards

            x = (max_width - width_mm) / 2  # center horizontally
            pdf.image(image_file, x=x, y=y_cursor, w=width_mm, h=height_mm)
            y_cursor += height_mm + 5  # move down with spacing

        except Exception as e:
            print(f"Failed to load image {image_file}: {e}")
            
                

    
    os.makedirs(pdf_path, exist_ok=True)
    pdf.output(os.path.join(pdf_path, f"{pdf_name}.pdf"), "F")

pdf_generator(fileNames = FILENAMES, pdf_path = PDF_PATH, pdf_name = PDF_NAME)
pdf_generator(fileNames=["Report/PDF/CloudCraftz.png"], pdf_path='Report/PDF/', pdf_name='logo')


imagelist = ["Report/PDF/CloudCraftz.png", "Report/PDF/EIS_GLOBAL.png"]
cc_logo_save_path = "Report/PDF/logo.pdf"
def logo(imagelist = imagelist , logo_save_path = cc_logo_save_path):
    pdf = FPDF()
    # logo path
    # imagelist is the list with all image filenames
    # for image in imagelist:
    pdf.add_page()
    # x,y,w,h = 45,20,30,15 # position for cloudcraftz logo
    x,y,w,h = 165,20,26,10 # position for cloudcraftz logo
    pdf.image(imagelist[0],x,y,w,h) # cloudcraftz logo
    x,y,w,h = 25, 20, 15, 15 # # position for client logo
    pdf.image(imagelist[1],x,y,w,h) # client logo

    pdf.output(logo_save_path, "F")
# Cloudcraftz logo
logo(imagelist=imagelist, logo_save_path = cc_logo_save_path)

# cient_logo_save_path = "Report/PDF/client_logo.pdf"
# position for client logo

# logo(imagelist=imagelist, logo_save_path = cient_logo_save_path)


save_path = "Report/PDF/date.pdf"
def generate_date_on_pdf(save_path):
    today = date.today()

    # save FPDF() class into a
    # variable pdf
    pdf = FPDF()

    # Add a page
    pdf.add_page()

    # set style and size of font
    # that you want in the pdf
    pdf.set_font("Arial", size = 10)

    # create a cell
    pdf.cell(200, 10, txt = '                 ',
             ln = 1, align = 'R')

    #another cell
    pdf.cell(200, 10, txt = '                 ',
         ln = 2, align = 'R')

    #another cell
    # pdf.cell(200, 10, txt = '                 ',
    #      ln = 3, align = 'R')

    # add another cell
    pdf.cell(186, 10, txt = f"Date : {today}     ",
             ln = 3, align = 'R')

    pdf.set_font("Arial", size = 12)

#         # add another cell
#     pdf.cell(50, 10, txt = f"Optimization Method: {PDF_NAME}",
#              ln = 4, align = 'C')

    # save the pdf with name .pdf
    pdf.output(save_path)

generate_date_on_pdf(save_path)


# input_file = "./Report/PDF/input.pdf"
output_file = "Report/PDF/date_logo.pdf"
cc_logo_file = "Report/PDF/logo.pdf" # logo file
# client_logo_file = cient_logo_save_path
date_file = 'Report/PDF/date.pdf'
def merge_logo_and_date_to_singlepdf(output_file = output_file,
                             watermark_file = cc_logo_file, date_file = date_file):
    # define the reader and writer objects
    reader_input = PdfReader(date_file)
    writer_output = PdfWriter()
    watermark_input = PdfReader(watermark_file)
    watermark = watermark_input.pages[0]
    # client logo add
    # watermark_input2 = PdfReader(watermark_file2)
    # watermark2 = watermark_input2.pages[0]


    # go through the pages one after the next
    for current_page in range(len(reader_input.pages)):
        #print(current_page)
        merger = PageMerge(reader_input.pages[0])
        merger.add(watermark).render()
        # merger.add(watermark2).render()


    # write the modified content to disk
    writer_output.write(output_file, reader_input)

merge_logo_and_date_to_singlepdf(output_file = output_file,
                             watermark_file = cc_logo_file, date_file = date_file)

# output_file = "Report/PDF/date_cc_client_logo.pdf"
# watermark_file = cient_logo_save_path
# date_file = 'Report/PDF/date_logo.pdf'
# merge_logo_and_date_to_singlepdf(output_file = output_file, watermark_file=watermark_file, date_file=date_file)


input_file = f"{PDF_PATH}/{PDF_NAME}.pdf"
output_file = f"{PDF_PATH}/{PDF_NAME}.pdf"
watermark_file = "Report/PDF/date_logo.pdf" # logo file

def merge_logo_date_into_pdf(input_file = input_file, output_file = output_file,
                             watermark_file = watermark_file, date_file = date_file):
    # define the reader and writer objects
    reader_input = PdfReader(input_file)
    writer_output = PdfWriter()
    watermark_input = PdfReader(watermark_file)
    watermark = watermark_input.pages[0]

    date_input = PdfReader(date_file)
    date = date_input.pages[0]

    # go through the pages one after the next
    for current_page in range(len(reader_input.pages)):
        #print(current_page)
        merger = PageMerge(reader_input.pages[0])
        merger.add(watermark).render()
        merger.add(date).render()

    # write the modified content to disk
    writer_output.write(output_file, reader_input)

merge_logo_date_into_pdf()

print('keeping a copy of report for reference')
shutil.copy(output_file, os.path.join(output_dir_folder, f'{PDF_NAME}.pdf'))