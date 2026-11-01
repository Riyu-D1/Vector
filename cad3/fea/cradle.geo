// cad3/fea/cradle.geo - tet mesh of input/j4_cradle.step (2nd order, C3D10)
// mesh frame = A2b home pose (arm frame): J4 axis +Y at (96.4, 216.2),
// fore_r2 bolts along +Y, wrist hangs +X, gravity -Z.
// run:  $GMSH cradle.geo -setnumber cl 3 -setnumber clh 1.5 -
Merge "input/j4_cradle.step";
Mesh.ElementOrder = 2;
Mesh.CharacteristicLengthMax = cl;
Mesh.CharacteristicLengthFromCurvature = 1;
Mesh.MinimumElementsPerTwoPi = 24;
// fine at the servo pocket and the four bolt columns
Field[1] = Ball;  Field[1].XCenter = 84.0;  Field[1].YCenter = 0.0;
Field[1].ZCenter = 216.2;  Field[1].Radius = 30.0;
Field[1].VIn = clh;  Field[1].VOut = cl;  Field[1].Thickness = 6.0;
Field[2] = Ball;  Field[2].XCenter = 79.4;  Field[2].YCenter = 29.0;
Field[2].ZCenter = 216.2;  Field[2].Radius = 20.0;
Field[2].VIn = clh;  Field[2].VOut = cl;  Field[2].Thickness = 6.0;
Field[9] = Min;  Field[9].FieldsList = {1, 2};
Background Field = 9;
Physical Volume("cradle") = {Volume{:}};
Mesh 3;
Mesh.MshFileVersion = 2.2;
Save Sprintf("run/cradle_%g_%g.msh", cl, clh);
Printf("GMSH DONE nodes=%g elems=%g", Mesh.NbNodes, Mesh.NbElements);
Exit;
