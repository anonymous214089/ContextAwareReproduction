# ContextAwareReproduction
Code and Data for the paper "Context-aware Bug Reproduction for Mobile Apps"

## 1. Introduction
For the data used in this project, please go to the following link to download:[link](https://drive.google.com/file/d/1CUjaKigNHLSC2ZCzYuRbX4jMSZA8P_kS/view)

For running video recordings of ScropDroid, please go to the following link to download:

## 2. Details of the Datasets Used in Our Experiments

For the 67 bug reports that at least one tool can successfully reproduce:
- Number of GUI events described in bug reports (donate as **Step**): average: 2.61, min: 1, max: 8
- Number of states included in the app (donate as **States**): average: 14.77, min: 1, max: 39
- Number of components in the app (donate as **Components**): average: 92.23, min: 7, max: 286

The details of each report are as follows

#### Details of ReCDroids's Dataset
| **id** | **\#Bug Report** | **Step** | **States** | **Components** | **id** | **\#Bug Report** | **Step** | **States** | **Components** |
|--------|------------------|----------|------------|----------------|--------|------------------|----------|------------|----------------|
| 1      | NewsBlur\-1053   | 5        | 8          | 25             | 17     | Transistor\-63   | 3        | 6          | 13             |
| 2      | Markor\-194      | 3        | 23         | 176            | 18     | Zom\-271         | 3        | 10         | 41             |
| 3      | Birthdroid\-13   | 1        | 9          | 28             | 19     | Pix\-Art\-125    | 2        | 15         | 75             |
| 4      | Car Report\-43   | 1        | 14         | 75             | 20     | Pix\-Art\-127    | 3        | 15         | 73             |
| 5      | Sudoku\-173      | 8        | 19         | 112            | 21     | ScreenCam\-25    | 4        | 15         | 110            |
| 6      | ACV\-22          | 4        | 19         | 144            | 22     | Ventriloid\-1    | 2        | 9          | 29             |
| 7      | AnyMemo\-18      | 2        | 25         | 134            | 23     | ownCloud\-487    | 1        | 8          | 40             |
| 8      | AnyMemo\-440     | 5        | 26         | 145            | 24     | OBDReader\-22    | 4        | 12         | 43             |
| 9      | Notepad\-23      | 2        | 19         | 65             | 25     | Dagger\-46       | 1        | 5          | 8              |

#### Details of AndroR2 Dataset
| **id** | **#Bug Report** | **Step** | **States** | **Components** | **id** | **#Bug Report** | **Step** | **States** | **Components** |
|--------|-----------------|----------|------------|----------------|--------|-----------------|----------|------------|----------------|
| 33     | HABPanel-25     | 1        | 7          | 7              | 39     |  K-9Mail-3255   | 2        | 13         | 109            |
| 34     | Noad Player-1   | 1        | 1          | 14             | 40     |  K-9Mail-3971   | 2        | 11         | 59             |
| 35     | Weather-61      | 2        | 5          | 18             | 41     | Hex-9           | 2        | 13         | 106            |
| 36     | Berkeley-82     | 1        | 11         | 27             | 42     | Firefox-3932    | 3        | 20         | 103            |
| 37     | OpenMap-1030    | 3        | 15         | 81             | 43     | Aegis-3932      | 2        | 26         | 117            |
| 38     | andOTP-500      | 3        | 15         | 73             |        |                 |          |            |                |

#### Details of ScopeDroid's Dataset
| **id** | **#Bug Report** | **Step** | **States** | **Components** | **id** | **#Bug Report** | **Step** | **States** | **Components** |
|--------|-----------------|----------|------------|----------------|--------|-----------------|----------|------------|----------------|
| 44     | NewPipe-7825    | 3        | 17         | 177            | 56     | WhereUGo-368    | 5        | 18         | 85             |
| 45     | SDBViewer-10    | 6        | 11         | 31             | 57     | FoodTracker-55  | 0        | 8          | 83             |
| 46     | Anki-9914       | 0        | 25         | 234            | 58     | GrowTracker-87  | 6        | 16         | 151            |
| 47     | Anki-10584      | 1        | 26         | 175            | 59     | Markor-1565     | 1        | 25         | 203            |
| 48     | Alarmio-47      | 1        | 12         | 134            | 60     | nRF Mesh-495    | 3        | 17         | 83             |
| 49     | plusTimer-19    | 3        | 12         | 153            | 61     | SDBViewer-7     | 2        | 13         | 32             |
| 50     | GrowTracker-89  | 5        | 15         | 148            | 62     | FakeStandby-30  | 3        | 15         | 72             |
| 51     | Shuttle-456     | 6        | 20         | 218            | 63     | pedometer-101   | 1        | 8          | 78             |
| 52     | Anki-3370       | 2        | 32         | 195            | 64     | Revolution-183  | 3        | 16         | 147            |
| 53     | Anki-2765       | 3        | 24         | 131            | 65     | Anki-3224       | 2        | 32         | 202            |
| 54     | Anki-2564       | 3        | 26         | 136            | 66     | getodk-219      | 2        | 6          | 19             |
| 55     | Anki-2681       | 3        | 29         | 164            | 67     | Anitrend-110    | 1        | 1          | 10             |
