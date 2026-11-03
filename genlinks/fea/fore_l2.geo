// genlinks auto: remesh <part>_gen.stl -> C3D10 tet mesh
Merge "/Users/deepakdiwan/Vector-wt/genlinks/genlinks/out/fore_l2_gen.stl";
Surface Loop(1) = {1};
Volume(1) = {1};
Mesh.ElementOrder = 2;
Mesh.HighOrderOptimize = 2;
Mesh.CharacteristicLengthMax = 1.50;
Mesh.CharacteristicLengthMin = 0.38;
Mesh.CharacteristicLengthFromCurvature = 1;
Mesh.MinimumElementsPerTwoPi = 14;
Mesh 3;
Mesh.MshFileVersion = 2.2;
Save "/Users/deepakdiwan/Vector-wt/genlinks/genlinks/fea/fore_l2.msh";
Exit;
