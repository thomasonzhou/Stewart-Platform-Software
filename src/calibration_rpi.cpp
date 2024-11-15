
#include <iostream>
#include <opencv2/calib3d.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/objdetect/charuco_detector.hpp>
#include <vector>
#include <lccv.hpp>

#include "aruco_samples_utility.hpp"
#include "camera_info.hpp"

using namespace std;
using namespace cv;

// -d=10 -h=2 -w=2 -sl=0.04 -ml=0.02 out
namespace {
const char* about =
    "Calibration using a ChArUco board\n"
    "  To capture a frame for calibration, press 'c',\n"
    "  If input comes from video, press any key for next frame\n"
    "  To finish capturing, press 'ESC' key and calibration starts.\n";
const char* keys =
    "{@outfile |cam.yml| Output file with calibrated camera parameters }"
    "{ci       | 0     | Camera id if input doesnt come from video (-v) }"
    "{dp       |       | File of marker detector parameters }"
    "{rs       | false | Apply refind strategy }"
    "{zt       | false | Assume zero tangential distortion }"
    "{a        |       | Fix aspect ratio (fx/fy) to this value }"
    "{pc       | false | Fix the principal point at the center }"
    "{sc       | false | Show detected chessboard corners after calibration }";
}  // namespace

int main(int argc, char* argv[]) {
  CommandLineParser parser(argc, argv, keys);
  parser.about(about);

  string outputFile = "calib.yml";

  bool showChessboardCorners = true;

  int calibrationFlags = 0;
  float aspectRatio = 1;
  if (parser.has("a")) {
    calibrationFlags |= CALIB_FIX_ASPECT_RATIO;
    aspectRatio = parser.get<float>("a");
  }
  if (parser.get<bool>("zt")) calibrationFlags |= CALIB_ZERO_TANGENT_DIST;
  if (parser.get<bool>("pc")) calibrationFlags |= CALIB_FIX_PRINCIPAL_POINT;

  aruco::DetectorParameters detectorParams =
      readDetectorParamsFromCommandLine(parser);
  cv::aruco::Dictionary dictionary =
      cv::aruco::getPredefinedDictionary(ARUCOTAG_DICTIONARY);

  bool refindStrategy = parser.get<bool>("rs");
  int camId = parser.get<int>("ci");
  String video;

  if (!parser.check()) {
    parser.printErrors();
    return 0;
  }

  //set up rpi camera
  cv::Mat image;
  lccv::PiCamera cam;
  cam.options->video_width=1024;
  cam.options->video_height=768;
  cam.options->framerate=5;
  cam.options->verbose=true;
  cam.startVideo();

  int ch=0;

  int waitTime;

  aruco::CharucoParameters charucoParams;
  if (refindStrategy) {
    charucoParams.tryRefineMarkers = true;
  }

  // Create charuco board object and CharucoDetector
  aruco::CharucoBoard board(Size(squaresX, squaresY), CHARUCO_SQUARE_PIXELS,
                            CHARUCO_MARKER_PIXELS, dictionary);
  aruco::CharucoDetector detector(board, charucoParams, detectorParams);

  vector<Mat> allCharucoCorners, allCharucoIds;

  vector<vector<Point2f>> allImagePoints;
  vector<vector<Point3f>> allObjectPoints;

  vector<Mat> allImages;
  Size imageSize;

  while (cam.getVideoFrame(image,1000) and allImagePoints.size() < 50) {
    Mat imageCopy;

    vector<int> markerIds;
    vector<vector<Point2f>> markerCorners;
    Mat currentCharucoCorners, currentCharucoIds;
    vector<Point3f> currentObjectPoints;
    vector<Point2f> currentImagePoints;

    // Detect ChArUco board
    detector.detectBoard(image, currentCharucoCorners, currentCharucoIds);
    //! [CalibrationWithCharucoBoard1]

    // Draw results
    image.copyTo(imageCopy);
    if (!markerIds.empty()) {
      aruco::drawDetectedMarkers(imageCopy, markerCorners);
    }

    if (currentCharucoCorners.total() > 3) {
      aruco::drawDetectedCornersCharuco(imageCopy, currentCharucoCorners,
                                        currentCharucoIds);
    }

    std::string message =
        "Images taken: " + std::to_string(allImages.size()) +
        " Press 'c' to add current frame. 'ESC' to finish and calibrate";
    putText(imageCopy, message, Point(10, 20), FONT_HERSHEY_SIMPLEX, 0.5,
            Scalar(255, 0, 0), 2);

    imshow("out", imageCopy);

    // Wait for key pressed
    char key = (char)waitKey(waitTime);

    //! [CalibrationWithCharucoBoard2]
    if (key == 'c' && currentCharucoCorners.total() > 3) {
      // Match image points
      board.matchImagePoints(currentCharucoCorners, currentCharucoIds,
                             currentObjectPoints, currentImagePoints);

      if (currentImagePoints.empty() || currentObjectPoints.empty()) {
        cout << "Point matching failed, try again." << endl;
        continue;
      }

      cout << "Frame captured" << endl;

      allCharucoCorners.push_back(currentCharucoCorners);
      allCharucoIds.push_back(currentCharucoIds);
      allImagePoints.push_back(currentImagePoints);
      allObjectPoints.push_back(currentObjectPoints);
      allImages.push_back(image);

      imageSize = image.size();
    }
  }

  //teardown
  cam.stopVideo();

  if (allCharucoCorners.size() < 4) {
    cerr << "Not enough corners for calibration" << endl;
    return 0;
  }

  //! [CalibrationWithCharucoBoard3]
  Mat cameraMatrix, distCoeffs;

  if (calibrationFlags & CALIB_FIX_ASPECT_RATIO) {
    cameraMatrix = Mat::eye(3, 3, CV_64F);
    cameraMatrix.at<double>(0, 0) = aspectRatio;
  }

  // Calibrate camera using ChArUco
  double repError = calibrateCamera(
      allObjectPoints, allImagePoints, imageSize, cameraMatrix, distCoeffs,
      noArray(), noArray(), noArray(), noArray(), noArray(), calibrationFlags);
  //! [CalibrationWithCharucoBoard3]

  bool saveOk =
      saveCameraParams(outputFile, imageSize, aspectRatio, calibrationFlags,
                       cameraMatrix, distCoeffs, repError);

  if (!saveOk) {
    cerr << "Cannot save output file" << endl;
    return 0;
  }

  cout << "Rep Error: " << repError << endl;
  cout << "Calibration saved to " << outputFile << endl;

  // Show interpolated charuco corners for debugging
  if (showChessboardCorners) {
    for (size_t frame = 0; frame < allImages.size(); frame++) {
      Mat imageCopy = allImages[frame].clone();

      if (allCharucoCorners[frame].total() > 0) {
        aruco::drawDetectedCornersCharuco(imageCopy, allCharucoCorners[frame],
                                          allCharucoIds[frame]);
      }

      imshow("out", imageCopy);
      char key = (char)waitKey(0);
    }
  }
}