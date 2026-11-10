// toolchg auto: mesh /Users/deepakdiwan/Vector-wt/refine/refine/out/stock_w_grip_frame.step -> C3D10 tet mesh
SetFactory("OpenCASCADE");
Merge "/Users/deepakdiwan/Vector-wt/refine/refine/out/stock_w_grip_frame.step";
Mesh.ElementOrder = 2;
Mesh.HighOrderOptimize = 2;
Mesh.CharacteristicLengthMax = 1.50;
Mesh.CharacteristicLengthMin = 0.38;
Mesh.CharacteristicLengthFromCurvature = 1;
Mesh.MinimumElementsPerTwoPi = 14;
Mesh 3;
Mesh.MshFileVersion = 2.2;
Save "/Users/deepakdiwan/Vector-wt/refine/refine/fea/stock_w_grip_frame.msh";
Exit;
