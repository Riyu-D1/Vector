// genlinks auto: remesh <part>_gen.stl -> C3D10 tet mesh
Merge "/Users/deepakdiwan/Vector-wt/genlinks/genlinks/out/link1_gen.stl";
Surface Loop(1) = {1};
Volume(1) = {1};
Mesh.ElementOrder = 2;
Mesh.HighOrderOptimize = 2;
Mesh.CharacteristicLengthMax = 3.00;
Mesh.CharacteristicLengthMin = 0.75;
Mesh.CharacteristicLengthFromCurvature = 1;
Mesh.MinimumElementsPerTwoPi = 14;
Mesh 3;
Mesh.MshFileVersion = 2.2;
Save "/Users/deepakdiwan/Vector-wt/genlinks/genlinks/fea/link1.msh";
Exit;
